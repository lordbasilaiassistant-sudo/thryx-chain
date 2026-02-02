/**
 * Expose THRYX RPC publicly via free tunnel
 * No signup required, no cost
 */
const { exec } = require('child_process');
const https = require('https');
const http = require('http');

const LOCAL_PORT = 8545;

// Try multiple free tunnel services
async function tryLocaltunnel() {
    return new Promise((resolve, reject) => {
        console.log('[TUNNEL] Trying localtunnel...');
        const lt = exec(`npx localtunnel --port ${LOCAL_PORT}`, (err) => {
            if (err) reject(err);
        });
        
        lt.stdout.on('data', (data) => {
            const match = data.match(/your url is: (https:\/\/[^\s]+)/i);
            if (match) {
                resolve(match[1]);
            }
            console.log(data);
        });
        
        lt.stderr.on('data', (data) => {
            console.error(data);
        });
        
        // Timeout after 30 seconds
        setTimeout(() => reject(new Error('Timeout')), 30000);
    });
}

async function createSimpleProxy() {
    // Create a simple HTTP server that proxies to the RPC
    const server = http.createServer((req, res) => {
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        
        if (req.method === 'OPTIONS') {
            res.writeHead(200);
            res.end();
            return;
        }
        
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            const options = {
                hostname: 'localhost',
                port: LOCAL_PORT,
                path: '/',
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            };
            
            const proxyReq = http.request(options, (proxyRes) => {
                let data = '';
                proxyRes.on('data', chunk => data += chunk);
                proxyRes.on('end', () => {
                    res.writeHead(proxyRes.statusCode, { 'Content-Type': 'application/json' });
                    res.end(data);
                });
            });
            
            proxyReq.on('error', (e) => {
                res.writeHead(500);
                res.end(JSON.stringify({ error: e.message }));
            });
            
            proxyReq.write(body);
            proxyReq.end();
        });
    });
    
    server.listen(8546, '0.0.0.0', () => {
        console.log('[PROXY] CORS proxy running on http://0.0.0.0:8546');
    });
}

async function main() {
    console.log('============================================================');
    console.log('           THRYX PUBLIC RPC EXPOSURE');
    console.log('============================================================');
    console.log('');
    
    // First, verify local RPC is running
    try {
        const testReq = http.request({
            hostname: 'localhost',
            port: LOCAL_PORT,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }, (res) => {
            console.log('[CHECK] Local RPC is running on port', LOCAL_PORT);
        });
        testReq.write(JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_blockNumber', params: [] }));
        testReq.end();
    } catch (e) {
        console.error('[ERROR] Local RPC not running. Start docker-compose first.');
        process.exit(1);
    }
    
    // Start CORS proxy
    await createSimpleProxy();
    
    // Try to get a public URL
    try {
        const url = await tryLocaltunnel();
        console.log('');
        console.log('============================================================');
        console.log('   YOUR PUBLIC THRYX RPC IS LIVE!');
        console.log('============================================================');
        console.log('');
        console.log('   Public URL:', url);
        console.log('   Chain ID: 31337');
        console.log('');
        console.log('   Add to MetaMask:');
        console.log('   - Network Name: THRYX');
        console.log('   - RPC URL:', url);
        console.log('   - Chain ID: 31337');
        console.log('   - Currency: ETH');
        console.log('');
        console.log('============================================================');
    } catch (e) {
        console.log('');
        console.log('[INFO] Could not start tunnel. Local access only.');
        console.log('[INFO] To expose publicly, install ngrok: https://ngrok.com/download');
        console.log('[INFO] Then run: ngrok http 8545');
        console.log('');
        console.log('Local RPC: http://localhost:8545');
        console.log('Local Proxy (CORS enabled): http://localhost:8546');
    }
}

main().catch(console.error);
