import 'package:flutter/material.dart';
import 'sync_merger.dart';

/// Show a conflict resolution dialog and return the user's choice
Future<ConflictResolution> showConflictDialog(
  BuildContext context,
  ConflictInfo conflict,
) async {
  final result = await showDialog<ConflictResolution>(
    context: context,
    barrierDismissible: false,
    builder: (context) => ConflictResolverDialog(conflict: conflict),
  );
  return result ?? ConflictResolution.cancel;
}

class ConflictResolverDialog extends StatelessWidget {
  final ConflictInfo conflict;

  const ConflictResolverDialog({super.key, required this.conflict});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: Colors.orange),
          SizedBox(width: 8),
          Text('Sync Conflict'),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            conflict.description,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          const Text('was modified on both devices.'),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Local',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Modified: ${conflict.localModified.substring(0, 19.clamp(0, conflict.localModified.length))}',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Remote',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Modified: ${conflict.remoteModified.substring(0, 19.clamp(0, conflict.remoteModified.length))}',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, ConflictResolution.keepLocal),
          child: const Text('Keep Local'),
        ),
        TextButton(
          onPressed: () =>
              Navigator.pop(context, ConflictResolution.keepRemote),
          child: const Text('Keep Remote'),
        ),
        TextButton(
          onPressed: () =>
              Navigator.pop(context, ConflictResolution.alwaysLocal),
          child: const Text('Always Local'),
        ),
        TextButton(
          onPressed: () =>
              Navigator.pop(context, ConflictResolution.alwaysRemote),
          child: const Text('Always Remote'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, ConflictResolution.cancel),
          style: TextButton.styleFrom(foregroundColor: Colors.red),
          child: const Text('Cancel'),
        ),
      ],
    );
  }
}
