import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class NestingService {
  constructor(configGetter) {
    this.configGetter = configGetter;
    this.activeJobs = new Map(); // jobId -> Promise
    this.completedJobs = new Map(); // jobId -> result
    this.recentLogs = [];
  }

  appendLog(msg) {
    const timestamp = new Date().toLocaleTimeString('vi-VN');
    const logItem = `[${timestamp}] ${msg}`;
    this.recentLogs.push(logItem);
    if (this.recentLogs.length > 500) {
      this.recentLogs.shift();
    }
    console.log(logItem);
    return logItem;
  }

  getLogs() {
    return this.recentLogs;
  }

  async runJob(jobData) {
    const jobId = jobData.id || `JOB-${Date.now()}`;

    // Check if already completed
    if (this.completedJobs.has(jobId)) {
      this.appendLog(`ℹ️ [Job Manager] Job '${jobId}' đã hoàn thành trước đó. Trả về kết quả từ Cache.`);
      return this.completedJobs.get(jobId);
    }

    // Check if currently running
    if (this.activeJobs.has(jobId)) {
      this.appendLog(`⚠️ [Job Manager] Job '${jobId}' đang chạy trong background. Chờ hoàn tất...`);
      return await this.activeJobs.get(jobId);
    }

    // Start execution promise
    const execPromise = this._executePythonNesting(jobData, jobId);
    this.activeJobs.set(jobId, execPromise);

    try {
      const result = await execPromise;
      this.completedJobs.set(jobId, result);
      return result;
    } finally {
      this.activeJobs.delete(jobId);
    }
  }

  _executePythonNesting(jobData, jobId) {
    return new Promise((resolve, reject) => {
      const backendDir = path.resolve(__dirname, '..');
      const cliScript = path.join(backendDir, 'src', 'run_job_cli.py');

      this.appendLog(`🚀 [PRINT JOB] Bắt đầu thực thi Job ID: ${jobId} (Order: ${jobData.order_id || 'N/A'})`);

      // Try 'python' or 'python3'
      const pythonProcess = spawn('python', [cliScript, '-'], {
        cwd: backendDir,
        env: {
          ...process.env,
          PYTHONIOENCODING: 'utf-8',
          PYTHONUNBUFFERED: '1'
        }
      });

      let stdoutData = '';
      let stderrData = '';
      const jobLogs = [];

      pythonProcess.stdout.on('data', (data) => {
        const str = data.toString('utf-8');
        stdoutData += str;

        const lines = str.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed && !trimmed.startsWith('__NESTING_RESULT_')) {
            jobLogs.push(trimmed);
            this.appendLog(trimmed);
          }
        }
      });

      pythonProcess.stderr.on('data', (data) => {
        const str = data.toString('utf-8');
        stderrData += str;
        console.error(`[Python stderr] ${str.trim()}`);
      });

      pythonProcess.on('close', (code) => {
        if (code !== 0 && !stdoutData.includes('__NESTING_RESULT_START__')) {
          const errMsg = `Nesting Engine process exited with code ${code}. Error: ${stderrData}`;
          this.appendLog(`❌ ${errMsg}`);
          return reject(new Error(errMsg));
        }

        try {
          const startIndex = stdoutData.indexOf('__NESTING_RESULT_START__');
          const endIndex = stdoutData.indexOf('__NESTING_RESULT_END__');

          if (startIndex !== -1 && endIndex !== -1) {
            const jsonText = stdoutData.substring(startIndex + '__NESTING_RESULT_START__'.length, endIndex).trim();
            const parsed = JSON.parse(jsonText);
            parsed.logs = [...(parsed.logs || []), ...jobLogs];
            this.appendLog(`🎉 [PRINT JOB COMPLETED] Hoàn thành Job ${jobId}!`);
            return resolve(parsed);
          } else {
            // Fallback parse
            const fallbackResult = {
              job_id: jobId,
              order_id: jobData.order_id,
              job_type: jobData.job_type || 'custom_nesting',
              status: 'completed',
              logs: jobLogs
            };
            return resolve(fallbackResult);
          }
        } catch (e) {
          this.appendLog(`❌ Lỗi phân tích kết quả output JSON: ${e.message}`);
          return reject(e);
        }
      });

      pythonProcess.on('error', (err) => {
        this.appendLog(`❌ Không thể khởi động Python process: ${err.message}`);
        reject(err);
      });

      // Send JSON payload via stdin
      pythonProcess.stdin.write(JSON.stringify(jobData));
      pythonProcess.stdin.end();
    });
  }
}
