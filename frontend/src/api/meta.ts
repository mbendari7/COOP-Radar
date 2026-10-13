/**
 * Public site settings from GET /api/config. Which optional features the server has on.
 */

import { useQuery } from '@tanstack/react-query'
import { apiFetch } from './client'

export interface PublicConfig {
  demo_enabled: boolean
  /** The site owner set their own Claude key, so visitors may use AI without bringing a key */
  server_ai_enabled: boolean
  /** Smart search and similar jobs are on */
  semantic_search_enabled: boolean
  /** AI actions per person per day on the owner's key. 0 means no limit. Own keys have none. */
  ai_daily_limit: number
}

export function usePublicConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => apiFetch<PublicConfig>('/api/config'),
    staleTime: Infinity, // only changes when the server is redeployed
  })
}
