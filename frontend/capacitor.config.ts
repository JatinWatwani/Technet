import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.vigilio.partner',
  appName: 'Vigilio Partner',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
}

export default config
