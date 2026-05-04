import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}))

vi.mock('../../api/client', () => ({
  api: {
    get: apiGet,
    post: apiPost,
    patch: apiPatch,
    delete: apiDelete,
  },
}))

import type { ConnectorTokenSummary } from '../../api/client'
import { Settings } from '../Settings'

const SETTINGS_RESPONSE = {
  timezone: 'UTC',
  transcript_enabled: true,
  crisis_disclaimer_acknowledged_at: null,
}

const ACTIVE_TOKEN: ConnectorTokenSummary = {
  id: 'tok-active-1',
  created_at: '2026-04-01T00:00:00Z',
  last_used_at: null,
  expires_at: '2026-08-01T00:00:00Z',
  revoked_at: null,
}

const REVOKED_TOKEN: ConnectorTokenSummary = {
  id: 'tok-revoked-1',
  created_at: '2026-03-01T00:00:00Z',
  last_used_at: '2026-04-15T12:00:00Z',
  expires_at: '2026-06-01T00:00:00Z',
  revoked_at: '2026-04-20T09:00:00Z',
}

const EXPIRED_TOKEN: ConnectorTokenSummary = {
  id: 'tok-expired-1',
  created_at: '2025-01-01T00:00:00Z',
  last_used_at: null,
  // Safely in the past so the branch fires regardless of test clock.
  expires_at: '2025-04-01T00:00:00Z',
  revoked_at: null,
}

const mockEndpoints = (tokens: ConnectorTokenSummary[] = []) => {
  apiGet.mockImplementation(async (path: string) => {
    if (path === '/settings') return SETTINGS_RESPONSE
    if (path === '/connect/tokens') return tokens
    throw new Error(`unexpected GET ${path}`)
  })
}

describe('Settings — connector tokens section', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPatch.mockReset()
    apiDelete.mockReset()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the empty state when there are no tokens', async () => {
    mockEndpoints([])
    render(<Settings />)
    expect(await screen.findByText(/no tokens yet/i)).toBeInTheDocument()
  })

  it('renders an active token row with status, created date, and last used', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    render(<Settings />)
    expect(await screen.findByText(/Active/)).toBeInTheDocument()
    expect(screen.getByText(/Last used never/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /^Revoke$/ }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Revoke and reissue/i }),
    ).toBeInTheDocument()
  })

  it('renders a revoked token row without action buttons', async () => {
    mockEndpoints([REVOKED_TOKEN])
    render(<Settings />)
    expect(await screen.findByText(/Revoked/)).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /^Revoke$/ }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Revoke and reissue/i }),
    ).not.toBeInTheDocument()
  })

  it('renders an expired token row without action buttons', async () => {
    mockEndpoints([EXPIRED_TOKEN])
    render(<Settings />)
    expect(await screen.findByText(/Expired/)).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /^Revoke$/ }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Revoke and reissue/i }),
    ).not.toBeInTheDocument()
  })

  it('treats a token expiring in the future as active', async () => {
    const ALMOST_EXPIRED: ConnectorTokenSummary = {
      ...ACTIVE_TOKEN,
      id: 'tok-active-future',
      // Future expiry — must render as Active.
      expires_at: new Date(Date.now() + 3600_000).toISOString(),
    }
    mockEndpoints([ALMOST_EXPIRED])
    render(<Settings />)
    expect(await screen.findByText(/Active/)).toBeInTheDocument()
  })

  it('revokes a token and refreshes the list', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    apiPost.mockResolvedValueOnce({})

    render(<Settings />)
    const revokeButton = await screen.findByRole('button', { name: /^Revoke$/ })

    fireEvent.click(revokeButton)

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(
        `/connect/tokens/${ACTIVE_TOKEN.id}/revoke`,
      )
    })
    // /settings on initial load + /connect/tokens on initial load + refresh
    await waitFor(() => {
      const tokenCalls = (apiGet as Mock).mock.calls.filter(
        (c) => c[0] === '/connect/tokens',
      )
      expect(tokenCalls.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('reissues a token by minting first, then revoking, then surfacing the new value', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    apiPost
      // mint runs first so a partial failure leaves the user with a working token
      .mockResolvedValueOnce({
        token: 'kdr_new_token_value_12345',
        created_at: '2026-05-04T00:00:00Z',
        expires_at: '2026-08-02T00:00:00Z',
      })
      .mockResolvedValueOnce({}) // revoke

    render(<Settings />)
    const reissueButton = await screen.findByRole('button', {
      name: /Revoke and reissue/i,
    })

    fireEvent.click(reissueButton)

    await waitFor(() => {
      expect(apiPost).toHaveBeenNthCalledWith(1, '/connect/token')
    })
    await waitFor(() => {
      expect(apiPost).toHaveBeenNthCalledWith(
        2,
        `/connect/tokens/${ACTIVE_TOKEN.id}/revoke`,
      )
    })
    expect(
      await screen.findByText(/kdr_new_token_value_12345/),
    ).toBeInTheDocument()
  })

  it('does nothing when the user cancels the revoke confirmation', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    render(<Settings />)
    const revokeButton = await screen.findByRole('button', { name: /^Revoke$/ })
    fireEvent.click(revokeButton)

    // No POST should fire — the confirm() guard is the only safety net for
    // an irreversible action; pin it.
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('does nothing when the user cancels the reissue confirmation', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    render(<Settings />)
    const reissueButton = await screen.findByRole('button', {
      name: /Revoke and reissue/i,
    })
    fireEvent.click(reissueButton)

    expect(apiPost).not.toHaveBeenCalled()
  })

  it('surfaces an error message if the initial token fetch fails', async () => {
    apiGet.mockImplementation(async (path: string) => {
      if (path === '/settings') return SETTINGS_RESPONSE
      if (path === '/connect/tokens') throw new Error('502 Bad Gateway')
      throw new Error(`unexpected GET ${path}`)
    })

    render(<Settings />)
    expect(
      await screen.findByText(/couldn't load tokens/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/502 Bad Gateway/)).toBeInTheDocument()
  })

  it('surfaces an error message if revoking fails', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    apiPost.mockRejectedValueOnce(new Error('500 Internal Server Error'))

    render(<Settings />)
    const revokeButton = await screen.findByRole('button', { name: /^Revoke$/ })
    fireEvent.click(revokeButton)

    expect(
      await screen.findByText(/couldn't load tokens/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/500 Internal Server Error/),
    ).toBeInTheDocument()
  })
})
