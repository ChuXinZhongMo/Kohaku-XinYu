export {}

type Cleanup = () => void

declare global {
  interface Window {
    xinyu: {
      getSnapshot: () => Promise<unknown>
      getProactiveInbox: () => Promise<unknown>
      getImpulseSoupState: () => Promise<unknown>
      getGatewayStatus: () => Promise<unknown>
      getStickerLibrary: () => Promise<unknown>
      runStickerMaintenance: (action: 'import-pending' | 'rebuild-index') => Promise<unknown>
      moveStickerToMood: (request: { file: string; mood: string }) => Promise<unknown>
      openStickerAssetDir: () => Promise<unknown>
      getQQEnvironmentStatus: () => Promise<unknown>
      startQQEnvironment: () => Promise<unknown>
      openNapCatWebUI: () => Promise<unknown>
      copyNapCatWebUIToken: () => Promise<unknown>
      getQQRuntimeConfig: () => Promise<unknown>
      setQQRuntimeConfig: (patch: {
        allowExternalPrivate?: boolean
        allowGroupMessages?: boolean
        allowedGroupIds?: string[]
        groupShadowEnabled?: boolean
        groupShadowAllowedGroupIds?: string[]
        blockedUserIds?: string[]
        blockedGroupIds?: string[]
        sendReplies?: boolean
      }) => Promise<unknown>
      restartQQGateway: () => Promise<unknown>
      sendChat: (request: {
        text: string
        commandId: string
        codexMode?: boolean
        allowLocalWrite?: boolean
        proactiveCandidateId?: string
        proactivePreview?: string
      }) => Promise<unknown>
      ackProactive: (request: { candidateId: string; action: 'read_locally' | 'approve_qq' | 'dismiss' | 'reply' }) => Promise<unknown>
      listMetabolismTickets: (statuses?: string) => Promise<unknown>
      yieldCompute: (request: { ticketId: string; seconds?: number; note?: string }) => Promise<unknown>
      maintainBoundary: (request: { ticketId: string; note?: string }) => Promise<unknown>
      onCoreEvent: (callback: (event: unknown) => void) => Cleanup
      onGatewayStatus: (callback: (status: unknown) => void) => Cleanup
    }
  }
}
