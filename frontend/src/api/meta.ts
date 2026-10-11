/**
 * Public app configuration (GET /api/config): which optional features the server has on.
 */

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from './client'

export interface PublicConfig {
  demo_enabled: boolean
  /** True when the server has both AI keys configured */
  ai_enabled: boolean
  /** AI actions (resume uploads + questions) per user per day; 0 = unlimited */
  ai_daily_limit: number
}

export function usePublicConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => apiFetch<PublicConfig>('/api/config'),
    staleTime: Infinity, // only changes when the server is redeployed
  })
}
