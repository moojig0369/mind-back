import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Mind-steps',
    short_name: 'Mind-steps',
    description: 'Сэтгэлзүйн туслах платформ',
    start_url: '/',
    display: 'standalone',
    background_color: '#000000',
    theme_color: '#7c3aed',
    icons: [
      {
        src: '/logo.png',
        sizes: '192x192',
        type: 'image/png',
      },
      {
        src: '/logo.png',
        sizes: '512x512',
        type: 'image/png',
      },
    ],
  }
}