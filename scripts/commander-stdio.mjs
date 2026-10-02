// Local-only bootstrap for an unmodified MIT upstream package.
// Deliberately excludes its remote, installer, flag fetch and Chrome download entrypoints.
const base = new URL('../vendor/desktop-commander/node_modules/@wonderwhy-er/desktop-commander/dist/', import.meta.url);
if (process.env.DESKTOP_COMMANDER_DISABLE_TELEMETRY !== '1') {
  throw new Error('Telemetry must be disabled before starting the local engine.');
}
global.disableOnboarding = true;
const { configManager } = await import(new URL('config-manager.js', base));
await configManager.init();
const config = await configManager.getConfig();
if (config.telemetryEnabled !== false || !config.allowedDirectories?.length) {
  throw new Error('Local configuration must disable telemetry and specify directories.');
}
const { FilteredStdioServerTransport } = await import(new URL('custom-stdio.js', base));
const { server } = await import(new URL('server.js', base));
const transport = new FilteredStdioServerTransport();
global.mcpTransport = transport;
server.oninitialized = () => transport.enableNotifications();
server.onclose = () => { process.exitCode = 0; };
await server.connect(transport);
