import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '2m', target: 100 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'],
  },
};

export default function () {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';

  const health = http.get(`${baseUrl}/health`);
  check(health, { 'health is 200': (r) => r.status === 200 });

  const stats = http.get(`${baseUrl}/api/v1/dashboard/stats`);
  check(stats, { 'stats valid status': (r) => [200, 401].includes(r.status) });

  sleep(1);
}
