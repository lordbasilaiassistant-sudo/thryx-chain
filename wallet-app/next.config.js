/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config, { isServer }) => {
    // Fallback for Node.js modules
    config.resolve.fallback = { 
      fs: false, 
      net: false, 
      tls: false,
    };
    
    // Handle problematic modules
    config.resolve.alias = {
      ...config.resolve.alias,
      'pino-pretty': false,
      'lokijs': false,
      'encoding': false,
    };
    
    // Ignore react-native modules
    config.module = config.module || {};
    config.module.rules = config.module.rules || [];
    config.module.rules.push({
      test: /\.js$/,
      include: /node_modules\/@metamask\/sdk/,
      resolve: {
        fullySpecified: false,
      },
    });
    
    // Provide empty modules for react-native dependencies
    config.resolve.alias['@react-native-async-storage/async-storage'] = require.resolve('./src/lib/empty-module.js');
    
    return config;
  },
  // Transpile specific packages
  transpilePackages: ['@metamask/sdk', '@walletconnect/ethereum-provider'],
}

module.exports = nextConfig
