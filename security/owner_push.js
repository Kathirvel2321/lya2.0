'use strict';
self.addEventListener('push', event => {
  let ticket;
  try { ticket = event.data.json().ticket; } catch (_) { return; }
  if (typeof ticket !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(ticket)) return;
  event.waitUntil(self.registration.showNotification('LYA needs your approval', {
    body: 'Tap to review the request from your laptop.',
    tag: 'lya-owner',
    data: {ticket}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const ticket = event.notification.data?.ticket;
  if (typeof ticket !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(ticket)) return;
  event.waitUntil(self.clients.openWindow('/#'+ticket));
});
