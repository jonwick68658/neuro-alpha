const CACHE_NAME = 'neurolm-v1';
const urlsToCache = [
  '/mobile',
  '/static/mobile.css',
  '/api/models',
  'icon.svg'
];

// Install event - cache resources
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached version or fetch from network
        return response || fetch(event.request);
      }
    )
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Background sync for offline messages
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    event.waitUntil(syncOfflineMessages());
  }
});

async function syncOfflineMessages() {
  // Get offline messages from IndexedDB and send to server
  // Implementation would handle queued messages when back online
}