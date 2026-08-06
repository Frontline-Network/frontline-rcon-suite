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

firebase.messaging();
