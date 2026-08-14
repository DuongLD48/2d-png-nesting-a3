import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class FirebaseService {
  constructor(configGetter) {
    this.configGetter = configGetter;
    this.processedJobs = new Set();
    this.isListening = false;
    this.timer = null;
  }

  getFirebaseConfig() {
    const cfg = this.configGetter();
    return cfg.firebase || {
      projectId: 'order-web-hoang',
      apiKey: 'AIzaSyC1SK8dB0FSz00EkeXErBdgp-SOeUj-HCU',
      auto_listen: true
    };
  }

  parseFirestoreDoc(docData) {
    const docName = docData?.name || '';
    const docId = docName ? docName.split('/').pop() : '';
    const fields = docData?.fields || {};

    const result = { id: docId };
    for (const [k, v] of Object.entries(fields)) {
      if (v.stringValue !== undefined) {
        result[k] = v.stringValue;
      } else if (v.integerValue !== undefined) {
        result[k] = parseInt(v.integerValue, 10);
      } else if (v.doubleValue !== undefined) {
        result[k] = parseFloat(v.doubleValue);
      } else if (v.booleanValue !== undefined) {
        result[k] = v.booleanValue;
      } else if (v.arrayValue !== undefined) {
        const arrVals = v.arrayValue?.values || [];
        result[k] = arrVals.map(x => x.stringValue ?? x.integerValue ?? '');
      }
    }
    return result;
  }

  async patchFirestoreDoc(collectionPath, docId, fieldsDict) {
    const fb = this.getFirebaseConfig();
    const projectId = fb.projectId || 'order-web-hoang';
    const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/${collectionPath}/${docId}`;

    const updateMasks = Object.keys(fieldsDict).map(k => `updateMask.fieldPaths=${k}`).join('&');
    const fullUrl = `${url}?${updateMasks}`;

    const fsFields = {};
    for (const [k, v] of Object.entries(fieldsDict)) {
      if (typeof v === 'boolean') {
        fsFields[k] = { booleanValue: v };
      } else if (typeof v === 'number') {
        if (Number.isInteger(v)) {
          fsFields[k] = { integerValue: String(v) };
        } else {
          fsFields[k] = { doubleValue: v };
        }
      } else if (Array.isArray(v)) {
        fsFields[k] = {
          arrayValue: {
            values: v.map(item => ({ stringValue: String(item) }))
          }
        };
      } else {
        fsFields[k] = { stringValue: String(v ?? '') };
      }
    }

    try {
      const resp = await axios.patch(fullUrl, { fields: fsFields }, {
        headers: { 'Content-Type': 'application/json' },
        timeout: 10000
      });
      return resp.status === 200 || resp.status === 204;
    } catch (err) {
      console.error(`[FirebaseService] Error patching ${collectionPath}/${docId}:`, err.message);
      return false;
    }
  }

  async updateJobCompleted(jobId, relativeFolder) {
    return await this.patchFirestoreDoc('print_jobs', jobId, {
      status: 'completed',
      output_folder: relativeFolder || '',
      completed_at: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });
  }

  async updateOrderPrintCompleted(orderId) {
    if (!orderId) return;
    const orderIds = String(orderId).split(',').map(s => s.trim()).filter(Boolean);

    for (const oid of orderIds) {
      const payload = {
        pod_print_status: 'completed',
        pod_print_status_text: 'Đã hoàn thành in',
        fulfillment_status_text: 'Hoàn thành in',
        sku_processed: true,
        updatedAt: new Date().toISOString()
      };

      const ok = await this.patchFirestoreDoc('MACCHOVUI', oid, payload);
      if (ok) {
        console.log(`✅ [FirebaseService] Đã cập nhật Trạng Thái POD đơn '${oid}' -> 'Đã hoàn thành in' trên MACCHOVUI!`);
      } else {
        // Fallback to 'orders' collection
        await this.patchFirestoreDoc('orders', oid, payload);
      }
    }
  }

  startListener(onJobReceived) {
    if (this.isListening) return;
    this.isListening = true;

    console.log('🟢 [FirebaseService] Background Firestore Realtime Listener Activated!');

    const poll = async () => {
      const fb = this.getFirebaseConfig();
      if (fb.auto_listen === false) {
        this.timer = setTimeout(poll, 15000);
        return;
      }

      let nextInterval = 15000;
      const projectId = fb.projectId || 'order-web-hoang';
      const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents:runQuery`;

      const queryPayload = {
        structuredQuery: {
          from: [{ collectionId: 'print_jobs' }],
          where: {
            fieldFilter: {
              field: { fieldPath: 'status' },
              op: 'EQUAL',
              value: { stringValue: 'pending' }
            }
          },
          limit: 5
        }
      };

      try {
        const resp = await axios.post(url, queryPayload, {
          headers: { 'Content-Type': 'application/json' },
          timeout: 12000
        });

        const items = resp.data || [];
        for (const item of items) {
          const docRaw = item?.document;
          if (!docRaw) continue;

          const jobData = this.parseFirestoreDoc(docRaw);
          const jobId = jobData.id;
          const status = jobData.status;

          if (status === 'pending' && !this.processedJobs.has(jobId)) {
            this.processedJobs.add(jobId);
            nextInterval = 2000; // Fast poll after detecting a job

            console.log(`\n⚡ [Firebase Realtime] Nhận Print Job mới: ${jobId} (Order: ${jobData.order_id || 'N/A'})`);

            if (onJobReceived) {
              try {
                const result = await onJobReceived(jobData);

                // Update Firestore
                await this.updateJobCompleted(jobId, result?.relative_folder);
                if (jobData.order_id) {
                  await this.updateOrderPrintCompleted(jobData.order_id);
                }
              } catch (err) {
                console.error(`❌ [Firebase Realtime] Lỗi xử lý job ${jobId}:`, err);
              }
            }
          }
        }
      } catch (err) {
        // Quota / Network error silent catch
      }

      this.timer = setTimeout(poll, nextInterval);
    };

    poll();
  }

  stopListener() {
    this.isListening = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    console.log('🔴 [FirebaseService] Listener stopped.');
  }
}
