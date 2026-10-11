/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin. Empty (default) = same origin via the Vite /api proxy. */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
