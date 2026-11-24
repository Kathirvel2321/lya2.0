// Exercise real Cloudflare MCP wrapping with a fixed fake executor; never evaluates code.
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { createNewsCodeServer, createWorkerNewsCodeServer } from './news.mjs';

const FIXTURE = `async () => {
  const all = await codemode.list_news({ source: 'all' });
  const other = await codemode.list_news({ source: 'fixture-two' });
  return [...new Map([...all.items, ...other.items].map(item => [item.id, item])).values()];
}`;
const executor = {
  async execute(code, providers) {
    assert.equal(code, FIXTURE);
    assert.equal(providers.length, 1);
    assert.equal(providers[0].name, 'codemode');
    const all = await providers[0].fns.list_news({ source: 'all' });
    const other = await providers[0].fns.list_news({ source: 'fixture-two' });
    const unique = [...new Map([...all.items, ...other.items].map(item => [item.id, item])).values()];
    return { result: unique };
  },
};
const server = await createNewsCodeServer(executor);
const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
const client = new Client({ name: 'lya-test', version: '0.0.0' });
await server.connect(serverTransport);
await client.connect(clientTransport);
try {
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map(tool => tool.name), ['code']);
  assert.match(tools[0].description, /list_news/);
  const reply = await client.callTool({ name: 'code', arguments: { code: FIXTURE } });
  assert.equal(reply.isError, undefined);
  const result = JSON.parse(reply.content[0].text);
  assert.deepEqual(result.map(item => item.id), ['a', 'b']);
  const bad = await client.callTool({ name: 'code', arguments: { code: 'different code' } });
  assert.equal(bad.isError, true);
  await assert.rejects(createWorkerNewsCodeServer(null), /Worker Loader binding required/);
  console.log(JSON.stringify({ passed: true, sdk: '@cloudflare/codemode', mcp_wrapper: true,
    fixture_executor_only: true, generated_code_executed: false, worker_sandbox_tested: false,
    fake_data_only: true, network_calls: false }));
} finally {
  await client.close();
  await server.close();
}
