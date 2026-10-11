/**
 * Public app configuration (GET /api/config): which optional features the server has on.
 */

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from './client'

export interface PublicConfig {
  demo_enabled: boolean
  /** The site owner set their own Claude key, so visitors may use AI without bringing a key */
  server_ai_enabled: boolean
  /** Smart (semantic) search + similar postings are available */
  semantic_search_enabled: boolean
  /** AI actions per user per day on the owner's key; 0 = unlimited. Own keys aren't limited. */
  ai_daily_limit: number
}

export function usePublicConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => apiFetch<PublicConfig>('/api/config'),
    staleTime: Infinity, // only changes when the server is redeployed
  })
}
