import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

/// Firebase options that are required when Frontline runs in a browser.
///
/// Android and iOS load their own options from the native Firebase files. The
/// web configuration is public application identity metadata, not a server
/// credential. Message delivery is still protected by Firebase's VAPID key and
/// the relay's service-account credential.
const webFirebaseOptions = FirebaseOptions(
  apiKey: 'AIzaSyCznTCGaE2lU7qUFIB2grmujpjQp9soMcE',
  appId: '1:1050619413922:web:2ff7a5272de985aa8c9efb',
  messagingSenderId: '1050619413922',
  projectId: 'frontline-6cb8a',
  authDomain: 'frontline-6cb8a.firebaseapp.com',
  storageBucket: 'frontline-6cb8a.firebasestorage.app',
  measurementId: 'G-Y7XGZM3RDB',
);

FirebaseOptions? get firebaseOptionsForCurrentPlatform =>
    kIsWeb ? webFirebaseOptions : null;
