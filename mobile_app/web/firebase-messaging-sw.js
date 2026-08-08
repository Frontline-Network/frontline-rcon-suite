/* global firebase */
// Firebase requires this root-level worker for notifications received while the
// Frontline PWA is in the background. It contains public app metadata only.
importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: 'AIzaSyCznTCGaE2lU7qUFIB2grmujpjQp9soMcE',
  authDomain: 'frontline-6cb8a.firebaseapp.com',
  projectId: 'frontline-6cb8a',
  storageBucket: 'frontline-6cb8a.firebasestorage.app',
  messagingSenderId: '1050619413922',
  appId: '1:1050619413922:web:2ff7a5272de985aa8c9efb',
});

const messaging = firebase.messaging();

// CRCON sends an intentionally opaque data payload. Turn it into a generic
// system notification only while the PWA is in the background; neither player
// names nor report text ever leave CRCON as part of this notification.
messaging.onBackgroundMessage((payload) => {
  const eventType = payload && payload.data && payload.data.event_type;
  const body = eventType === 'created'
    ? 'Eine neue Meldung wartet auf Bearbeitung.'
    : 'Ein Vorfall wurde aktualisiert.';
  const data = (payload && payload.data) || {};
  self.registration.showNotification('Frontline', {
    body,
    icon: '/icons/Icon-192.png',
    // Android turns notification badges into a monochrome status-bar glyph.
    // This asset has a transparent canvas, so only the Frontline mark is
    // rendered instead of a solid white square.
    badge: '/icons/frontline-notification-badge.svg',
    tag: `frontline-${data.incident_id || 'incident'}`,
    data,
  });
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        if (clients.length > 0) return clients[0].focus();
        return self.clients.openWindow('/');
      }),
  );
});
