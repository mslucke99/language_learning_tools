import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';

enum AdPlacement { none, top, bottom }

class AdService extends ChangeNotifier {
  static const String _prefKey = 'ad_placement';

  // Check if running on a supported mobile platform
  static bool get isSupportedPlatform {
    return Platform.isAndroid || Platform.isIOS;
  }

  // Test Ad Unit IDs (safe for development)
  // Replace with real IDs before release
  static String get bannerAdUnitId {
    if (Platform.isAndroid) {
      return 'ca-app-pub-3940256099942544/6300978111'; // Android Test Banner
    } else if (Platform.isIOS) {
      return 'ca-app-pub-3940256099942544/2934735716'; // iOS Test Banner
    }
    throw UnsupportedError('Ads are only supported on Android and iOS');
  }

  AdPlacement _placement = AdPlacement.none;
  BannerAd? _bannerAd;
  bool _isAdLoaded = false;

  AdPlacement get placement => _placement;
  BannerAd? get bannerAd => _bannerAd;
  bool get isAdLoaded => _isAdLoaded;
  bool get showAd => _placement != AdPlacement.none && _isAdLoaded;

  Future<void> initialize() async {
    // Only initialize ads on supported mobile platforms
    if (!isSupportedPlatform) {
      _placement = AdPlacement.none;
      notifyListeners();
      return;
    }
    
    await MobileAds.instance.initialize();
    await _loadPreference();
    if (_placement != AdPlacement.none) {
      await loadBannerAd();
    }
  }

  Future<void> _loadPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final index = prefs.getInt(_prefKey) ?? 0;
    _placement = AdPlacement.values[index];
    notifyListeners();
  }

  Future<void> setPlacement(AdPlacement newPlacement) async {
    // On unsupported platforms, always keep ads disabled
    if (!isSupportedPlatform) {
      if (_placement != AdPlacement.none) {
        _placement = AdPlacement.none;
        notifyListeners();
      }
      return;
    }

    if (_placement == newPlacement) return;

    _placement = newPlacement;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_prefKey, newPlacement.index);

    if (newPlacement == AdPlacement.none) {
      _bannerAd?.dispose();
      _bannerAd = null;
      _isAdLoaded = false;
    } else if (!_isAdLoaded) {
      await loadBannerAd();
    }

    notifyListeners();
  }

  Future<void> loadBannerAd() async {
    // Only load ads on supported mobile platforms
    if (!isSupportedPlatform) {
      _isAdLoaded = false;
      return;
    }

    _bannerAd = BannerAd(
      adUnitId: bannerAdUnitId,
      size: AdSize.banner,
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (ad) {
          _isAdLoaded = true;
          notifyListeners();
        },
        onAdFailedToLoad: (ad, error) {
          ad.dispose();
          _isAdLoaded = false;
          debugPrint('Banner ad failed to load: $error');
        },
      ),
    );
    await _bannerAd!.load();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
  }
}
