// Fixed synthetic records only. This module cannot access LYA's cache or the network.
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { codeMcpServer } from '@cloudflare/codemode/mcp';

const items = [
  { id: 'a', source: 'fixture-one', title: 'Synthetic agent update', url: 'https://example.invalid/a' },
  { id: 'a', source: 'fixture-one', title: 'Synthetic agent update', url: 'https://example.invalid/a' },
  { id: 'b', source: 'fixture-two', title: 'Synthetic model update', url: 'https://example.invalid/b' },
];

export async function createNewsCodeServer(executor) {
  const upstream = new McpServer({ name: 'lya-fake-news', version: '0.0.0' });
  upstream.registerTool('list_news', {
    description: 'List generated fake technology news records.',
    inputSchema: { source: z.enum(['all', 'fixture-one', 'fixture-two']) },
  }, async ({ source }) => ({
    structuredContent: { items: items.filter(item => source === 'all' || item.source === source) },
    content: [{ type: 'text', text: 'Synthetic fixture records.' }],
  }));
  return codeMcpServer({ server: upstream, executor });
}

// Only a Cloudflare Worker Loader can supply this binding; no local eval fallback.
export async function createWorkerNewsCodeServer(loader) {
  if (!loader) throw new Error('Cloudflare Worker Loader binding required.');
  const { DynamicWorkerExecutor } = await import('@cloudflare/codemode');
  return createNewsCodeServer(new DynamicWorkerExecutor({ loader, globalOutbound: null, timeout: 10000 }));
}
