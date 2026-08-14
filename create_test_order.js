/**
 * Script tạo đơn hàng & print job mẫu lên Firebase Firestore để kiểm thử Auto Nesting
 * Chạy bằng lệnh: node create_test_order.js
 */

const projectId = 'order-web-hoang';
const apiKey = 'AIzaSyC1SK8dB0FSz00EkeXErBdgp-SOeUj-HCU';

const orderCode = '#MCV-' + Math.floor(1000 + Math.random() * 9000);
const jobId = 'JOB-' + Date.now();

// Danh sách SKU mẫu có sẵn trong thư mục ANHLOCAL
const sampleSkus = ['01-T-L', '02-D-XL', '03-D-L'];

const payload = {
  id: jobId,
  order_id: orderCode,
  skus: sampleSkus,
  job_type: 'custom_nesting',
  job_type_label: 'In Decal Custom (390x290mm)',
  status: 'pending',
  customer_name: 'Khách Hàng Test',
  customer_phone: '0988889999',
  created_at: new Date().toISOString()
};

function toFirestoreValue(val) {
  if (val === null || val === undefined) return { nullValue: null };
  if (typeof val === 'boolean') return { booleanValue: val };
  if (typeof val === 'number') return { integerValue: String(val) };
  if (Array.isArray(val)) return { arrayValue: { values: val.map(toFirestoreValue) } };
  return { stringValue: String(val) };
}

const docBody = {
  fields: Object.fromEntries(
    Object.entries(payload).map(([k, v]) => [k, toFirestoreValue(v)])
  )
};

const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/print_jobs/${jobId}?key=${apiKey}`;

console.log('⏳ Đang gửi đơn test lên Firebase Firestore...');

fetch(url, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(docBody)
})
  .then(async (r) => {
    const res = await r.json();
    if (r.ok) {
      console.log('==================================================');
      console.log('✅ ĐÃ TẠO THÀNH CÔNG ĐƠN TEST LÊN FIREBASE FIRESTORE!');
      console.log('==================================================');
      console.log('🆔 Print Job ID:', jobId);
      console.log('📦 Mã Đơn Hàng:', orderCode);
      console.log('🏷️ Danh Sách SKU:', sampleSkus.join(', '));
      console.log('📐 Loại In:', payload.job_type_label);
      console.log('⚡ Trạng Thái:', payload.status.toUpperCase());
      console.log('==================================================');
      console.log('💡 Bạn có thể bật RUN_ALL.bat để server tự động nhận và xử lý đơn này!');
    } else {
      console.error('❌ Lỗi khi gửi dữ liệu lên Firebase:', res);
    }
  })
  .catch((err) => console.error('❌ Lỗi kết nối mạng:', err));
