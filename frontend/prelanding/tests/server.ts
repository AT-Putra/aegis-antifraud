import { setupServer } from "msw/node";

// MSW server bersama (handler di-set per-test via server.use()).
export const server = setupServer();
