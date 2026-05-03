export {}

type Cleanup = () => void

declare global {
  interface Window {
    xinyu: {
      getSnapshot: () => Promise<unknown>
      getGatewayStatus: () => Promise<unknown>
      sendChat: (request: { text: string; commandId: string }) => Promise<unknown>
      ackProactive: (request: { candidateId: string; action: 'read_locally' | 'approve_qq' | 'dismiss' }) => Promise<unknown>
      startService: (name: string) => Promise<unknown>
      onCoreEvent: (callback: (event: unknown) => void) => Cleanup
      onGatewayStatus: (callback: (status: unknown) => void) => Cleanup
    }
  }
}
