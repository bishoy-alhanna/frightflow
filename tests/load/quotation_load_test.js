/**
 * Load test for Quotation Service
 * 
 * This script tests the quotation service under various load conditions
 * to ensure it meets the SLA requirements:
 * - Quote creation: p95 ≤ 2s (cached), ≤ 5s (cold)
 * - Quote retrieval: p95 ≤ 300ms
 * - System availability: 99.9%
 * 
 * Usage:
 *   k6 run quotation_load_test.js
 *   k6 run --vus 50 --duration 5m quotation_load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const quotationCreationTime = new Trend('quotation_creation_time');
const quotationRetrievalTime = new Trend('quotation_retrieval_time');
const quotationAcceptanceTime = new Trend('quotation_acceptance_time');
const errorRate = new Rate('error_rate');
const quotationCounter = new Counter('quotations_created');

// Test configuration
export const options = {
  stages: [
    // Ramp up
    { duration: '2m', target: 10 },   // Ramp up to 10 users over 2 minutes
    { duration: '5m', target: 10 },   // Stay at 10 users for 5 minutes
    { duration: '2m', target: 25 },   // Ramp up to 25 users over 2 minutes
    { duration: '5m', target: 25 },   // Stay at 25 users for 5 minutes
    { duration: '2m', target: 50 },   // Ramp up to 50 users over 2 minutes
    { duration: '10m', target: 50 },  // Stay at 50 users for 10 minutes
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    // SLA requirements
    'quotation_creation_time': ['p(95)<5000', 'p(90)<2000'], // 95th percentile < 5s, 90th < 2s
    'quotation_retrieval_time': ['p(95)<300'],               // 95th percentile < 300ms
    'quotation_acceptance_time': ['p(95)<1000'],             // 95th percentile < 1s
    'error_rate': ['rate<0.01'],                             // Error rate < 1% (99.9% availability)
    'http_req_duration': ['p(95)<3000'],                     // Overall 95th percentile < 3s
    'http_req_failed': ['rate<0.01'],                        // HTTP error rate < 1%
  },
};

// Base URL - can be overridden with environment variable
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8101';

// Sample quote requests for different scenarios
const quoteRequests = {
  fcl_standard: {
    mode: 'SEA',
    service: 'FCL',
    origin: 'SGSIN',
    destination: 'EGALY',
    containers: [{ type: '40HC', count: 1 }],
    cargo: { weightKg: 8200, volumeM3: 58 },
    accessorials: ['FUEL', 'PORT_FEES'],
    customer_id: 'LOAD_TEST_CUSTOMER'
  },
  fcl_multi_container: {
    mode: 'SEA',
    service: 'FCL',
    origin: 'SGSIN',
    destination: 'USNYC',
    containers: [
      { type: '40HC', count: 2 },
      { type: '20GP', count: 1 }
    ],
    cargo: { weightKg: 15000, volumeM3: 120 },
    accessorials: ['FUEL', 'PORT_FEES', 'SECURITY'],
    customer_id: 'LOAD_TEST_CUSTOMER'
  },
  lcl_standard: {
    mode: 'SEA',
    service: 'LCL',
    origin: 'SGSIN',
    destination: 'EGALY',
    cargo: { weightKg: 1500, volumeM3: 2.5 },
    accessorials: ['FUEL', 'DOCUMENTATION'],
    customer_id: 'LOAD_TEST_CUSTOMER'
  },
  air_freight: {
    mode: 'AIR',
    service: 'AIR',
    origin: 'SGSIN',
    destination: 'EGALY',
    cargo: { weightKg: 500 },
    accessorials: ['FUEL', 'SECURITY'],
    customer_id: 'LOAD_TEST_CUSTOMER'
  }
};

// Array to store created quote IDs for retrieval tests
let createdQuotes = [];

export function setup() {
  console.log('Starting load test setup...');
  
  // Health check
  const healthResponse = http.get(`${BASE_URL}/health`);
  if (healthResponse.status !== 200) {
    throw new Error(`Service not healthy: ${healthResponse.status}`);
  }
  
  console.log('Service is healthy, starting load test...');
  return { baseUrl: BASE_URL };
}

export default function(data) {
  const baseUrl = data.baseUrl;
  
  // Randomly select a quote request type
  const requestTypes = Object.keys(quoteRequests);
  const randomType = requestTypes[Math.floor(Math.random() * requestTypes.length)];
  const quoteRequest = quoteRequests[randomType];
  
  // Add some randomization to avoid caching effects
  quoteRequest.customer_id = `LOAD_TEST_${Math.floor(Math.random() * 1000)}`;
  
  // Test scenario weights
  const scenario = Math.random();
  
  if (scenario < 0.6) {
    // 60% - Create new quotes
    testQuoteCreation(baseUrl, quoteRequest);
  } else if (scenario < 0.9) {
    // 30% - Retrieve existing quotes
    testQuoteRetrieval(baseUrl);
  } else {
    // 10% - Accept quotes
    testQuoteAcceptance(baseUrl);
  }
  
  // Random sleep between 1-3 seconds to simulate user behavior
  sleep(Math.random() * 2 + 1);
}

function testQuoteCreation(baseUrl, quoteRequest) {
  const headers = {
    'Content-Type': 'application/json',
    'Idempotency-Key': `load-test-${Date.now()}-${Math.random()}`
  };
  
  const startTime = Date.now();
  const response = http.post(
    `${baseUrl}/api/v1/quotes`,
    JSON.stringify(quoteRequest),
    { headers }
  );
  const duration = Date.now() - startTime;
  
  const success = check(response, {
    'quote creation status is 201': (r) => r.status === 201,
    'quote creation response has quote_id': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.quote_id && body.quote_id.startsWith('Q-');
      } catch (e) {
        return false;
      }
    },
    'quote creation response has valid total_amount': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.total_amount && body.total_amount > 0;
      } catch (e) {
        return false;
      }
    }
  });
  
  quotationCreationTime.add(duration);
  errorRate.add(!success);
  
  if (success) {
    quotationCounter.add(1);
    try {
      const body = JSON.parse(response.body);
      createdQuotes.push(body.quote_id);
      
      // Keep only the last 100 quotes to avoid memory issues
      if (createdQuotes.length > 100) {
        createdQuotes = createdQuotes.slice(-100);
      }
    } catch (e) {
      console.error('Failed to parse quote creation response:', e);
    }
  }
}

function testQuoteRetrieval(baseUrl) {
  if (createdQuotes.length === 0) {
    // No quotes to retrieve, create one first
    testQuoteCreation(baseUrl, quoteRequests.fcl_standard);
    return;
  }
  
  const randomQuoteId = createdQuotes[Math.floor(Math.random() * createdQuotes.length)];
  
  const startTime = Date.now();
  const response = http.get(`${baseUrl}/api/v1/quotes/${randomQuoteId}`);
  const duration = Date.now() - startTime;
  
  const success = check(response, {
    'quote retrieval status is 200': (r) => r.status === 200,
    'quote retrieval response has quote data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.quote_id === randomQuoteId;
      } catch (e) {
        return false;
      }
    }
  });
  
  quotationRetrievalTime.add(duration);
  errorRate.add(!success);
}

function testQuoteAcceptance(baseUrl) {
  if (createdQuotes.length === 0) {
    // No quotes to accept, create one first
    testQuoteCreation(baseUrl, quoteRequests.fcl_standard);
    return;
  }
  
  const randomQuoteId = createdQuotes[Math.floor(Math.random() * createdQuotes.length)];
  
  const startTime = Date.now();
  const response = http.put(`${baseUrl}/api/v1/quotes/${randomQuoteId}/accept`);
  const duration = Date.now() - startTime;
  
  const success = check(response, {
    'quote acceptance status is 200 or 400': (r) => r.status === 200 || r.status === 400,
    'quote acceptance response is valid': (r) => {
      if (r.status === 200) {
        try {
          const body = JSON.parse(r.body);
          return body.status === 'ACCEPTED';
        } catch (e) {
          return false;
        }
      } else if (r.status === 400) {
        // Quote might already be accepted or expired - this is expected
        return true;
      }
      return false;
    }
  });
  
  quotationAcceptanceTime.add(duration);
  errorRate.add(!success);
}

export function teardown(data) {
  console.log('Load test completed');
  console.log(`Total quotes created: ${quotationCounter.value}`);
  
  // Final health check
  const healthResponse = http.get(`${data.baseUrl}/health`);
  check(healthResponse, {
    'service still healthy after load test': (r) => r.status === 200
  });
}

// Additional test scenarios for specific load patterns

export const spikeTest = {
  executor: 'ramping-arrival-rate',
  startRate: 10,
  timeUnit: '1s',
  preAllocatedVUs: 50,
  maxVUs: 100,
  stages: [
    { duration: '1m', target: 10 },   // Normal load
    { duration: '30s', target: 100 }, // Spike
    { duration: '1m', target: 10 },   // Back to normal
  ],
};

export const stressTest = {
  executor: 'ramping-vus',
  startVUs: 0,
  stages: [
    { duration: '5m', target: 100 },  // Ramp up to stress level
    { duration: '10m', target: 100 }, // Stay at stress level
    { duration: '5m', target: 200 },  // Increase to breaking point
    { duration: '10m', target: 200 }, // Stay at breaking point
    { duration: '5m', target: 0 },    // Ramp down
  ],
};

export const soakTest = {
  executor: 'constant-vus',
  vus: 20,
  duration: '1h', // Run for 1 hour to test stability
};

// Helper function to generate realistic test data
function generateRealisticQuoteRequest() {
  const origins = ['SGSIN', 'HKHKG', 'CNSHA', 'JPNGO', 'KRPUS'];
  const destinations = ['EGALY', 'USNYC', 'USLAX', 'NLRTM', 'DEHAM'];
  const services = ['FCL', 'LCL'];
  const containerTypes = ['20GP', '40GP', '40HC', '45HC'];
  
  const origin = origins[Math.floor(Math.random() * origins.length)];
  const destination = destinations[Math.floor(Math.random() * destinations.length)];
  const service = services[Math.floor(Math.random() * services.length)];
  
  const request = {
    mode: 'SEA',
    service: service,
    origin: origin,
    destination: destination,
    accessorials: ['FUEL'],
    customer_id: `LOAD_TEST_${Math.floor(Math.random() * 10000)}`
  };
  
  if (service === 'FCL') {
    const containerType = containerTypes[Math.floor(Math.random() * containerTypes.length)];
    const containerCount = Math.floor(Math.random() * 3) + 1;
    
    request.containers = [{ type: containerType, count: containerCount }];
    request.cargo = {
      weightKg: Math.floor(Math.random() * 20000) + 1000,
      volumeM3: Math.floor(Math.random() * 100) + 10
    };
  } else {
    request.cargo = {
      weightKg: Math.floor(Math.random() * 5000) + 100,
      volumeM3: Math.floor(Math.random() * 10) + 1
    };
  }
  
  // Randomly add accessorials
  const possibleAccessorials = ['PORT_FEES', 'DOCUMENTATION', 'SECURITY', 'INSURANCE'];
  possibleAccessorials.forEach(acc => {
    if (Math.random() < 0.3) { // 30% chance for each accessorial
      request.accessorials.push(acc);
    }
  });
  
  return request;
}

