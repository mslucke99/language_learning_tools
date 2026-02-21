import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:io';
import '../services/ad_service.dart';

class AdSettingsScreen extends StatelessWidget {
  const AdSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final isMobile = Platform.isAndroid || Platform.isIOS;

    return Scaffold(
      appBar: AppBar(title: const Text('Ad Settings')),
      body: isMobile
          ? Consumer<AdService>(
              builder: (context, adService, child) {
                return ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    const Text(
                      'Support Getcha Fluentia',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Enabling ads helps support continued development of this free app. '
                      'You can choose where ads appear, or disable them entirely.',
                      style: TextStyle(color: Colors.grey),
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'Ad Placement',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 8),
                    RadioListTile<AdPlacement>(
                      title: const Text('None (Disabled)'),
                      subtitle: const Text('No ads will be shown'),
                      value: AdPlacement.none,
                      groupValue: adService.placement,
                      onChanged: (value) => adService.setPlacement(value!),
                    ),
                    RadioListTile<AdPlacement>(
                      title: const Text('Top'),
                      subtitle: const Text('Banner ad at the top of screens'),
                      value: AdPlacement.top,
                      groupValue: adService.placement,
                      onChanged: (value) => adService.setPlacement(value!),
                    ),
                    RadioListTile<AdPlacement>(
                      title: const Text('Bottom'),
                      subtitle: const Text('Banner ad at the bottom of screens'),
                      value: AdPlacement.bottom,
                      groupValue: adService.placement,
                      onChanged: (value) => adService.setPlacement(value!),
                    ),
                    const SizedBox(height: 24),
                    if (adService.placement != AdPlacement.none)
                      Card(
                        color: Colors.green.shade50,
                        child: const Padding(
                          padding: EdgeInsets.all(16),
                          child: Row(
                            children: [
                              Icon(Icons.favorite, color: Colors.green),
                              SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  'Thank you for supporting Getcha Fluentia!',
                                  style: TextStyle(color: Colors.green),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              },
            )
          : Center(
              child: Card(
                margin: const EdgeInsets.all(24),
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.info, size: 48, color: Colors.blue.shade700),
                      const SizedBox(height: 16),
                      Text(
                        'Ads Not Available',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Advertisements are only available on Android and iOS mobile devices. '
                        'You\'re running this on a desktop platform, so ads are not supported.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}
