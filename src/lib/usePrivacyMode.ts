import { useEffect, useState } from 'react'

export type PrivacyMode = 'off' | 'manual' | 'smart'

export function usePrivacyMode(): [PrivacyMode, (m: PrivacyMode) => void] {
  const [mode, setMode] = useState<PrivacyMode>('smart')

  useEffect(() => {
    chrome.storage.sync.get('privacyMode', (res) => {
      const v = res['privacyMode']
      if (v === 'off' || v === 'manual' || v === 'smart') setMode(v)
    })

    function onChange(
      changes: { [key: string]: chrome.storage.StorageChange },
      _area: string,
    ) {
      const v = changes['privacyMode']?.newValue
      if (v === 'off' || v === 'manual' || v === 'smart') setMode(v)
    }

    chrome.storage.onChanged.addListener(onChange)
    return () => chrome.storage.onChanged.removeListener(onChange)
  }, [])

  function update(m: PrivacyMode) {
    setMode(m)
    chrome.storage.sync.set({ privacyMode: m })
  }

  return [mode, update]
}
