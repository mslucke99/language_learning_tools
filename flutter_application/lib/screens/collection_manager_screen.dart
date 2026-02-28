import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/collection_service.dart';

class CollectionManagerScreen extends StatefulWidget {
  final String? language;

  const CollectionManagerScreen({
    super.key,
    this.language,
  });

  @override
  State<CollectionManagerScreen> createState() => _CollectionManagerScreenState();
}

class _CollectionManagerScreenState extends State<CollectionManagerScreen> {
  final CollectionService _collectionService = CollectionService();
  
  List<Collection> _collections = [];
  bool _isLoading = true;
  String? _selectedType;

  @override
  void initState() {
    super.initState();
    _loadCollections();
  }

  Future<void> _loadCollections() async {
    setState(() => _isLoading = true);
    
    try {
      final collections = await _collectionService.getCollections(
        type: _selectedType,
        language: widget.language,
      );

      setState(() {
        _collections = collections;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  Future<void> _createCollection() async {
    final nameController = TextEditingController();
    String selectedType = 'deck';

    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Create Collection'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(
                  labelText: 'Collection Name',
                ),
                autofocus: true,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: selectedType,
                decoration: const InputDecoration(
                  labelText: 'Type',
                ),
                items: const [
                  DropdownMenuItem(value: 'deck', child: Text('Decks')),
                  DropdownMenuItem(value: 'word', child: Text('Words')),
                  DropdownMenuItem(value: 'sentence', child: Text('Sentences')),
                  DropdownMenuItem(value: 'grammar', child: Text('Grammar')),
                ],
                onChanged: (value) => setState(() => selectedType = value!),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(context, {
                'name': nameController.text,
                'type': selectedType,
              }),
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );

    if (result != null && result['name'].toString().isNotEmpty) {
      await _collectionService.createCollection(
        name: result['name'],
        type: result['type'],
        language: widget.language,
      );
      _loadCollections();
    }
  }

  Future<void> _editCollection(Collection collection) async {
    final nameController = TextEditingController(text: collection.name);

    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Collection'),
        content: TextField(
          controller: nameController,
          decoration: const InputDecoration(
            labelText: 'Collection Name',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, nameController.text),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (result != null && result.isNotEmpty) {
      await _collectionService.updateCollection(
        collection.id!,
        name: result,
      );
      _loadCollections();
    }
  }

  Future<void> _deleteCollection(Collection collection) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Collection'),
        content: Text(
          'Delete "${collection.name}"? Items will become uncategorized.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await _collectionService.deleteCollection(collection.id!);
      _loadCollections();
    }
  }

  Future<void> _viewCollectionItems(Collection collection) async {
    final count = await _collectionService.getCollectionItemCount(
      collection.id!,
      collection.type,
    );

    if (mounted) {
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(collection.name),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Type: ${_getTypeLabel(collection.type)}'),
              Text('Items: $count'),
              if (collection.language != null)
                Text('Language: ${collection.language}'),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Collections'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              setState(() => _selectedType = value == 'all' ? null : value);
              _loadCollections();
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'all', child: Text('All Types')),
              const PopupMenuItem(value: 'deck', child: Text('Decks')),
              const PopupMenuItem(value: 'word', child: Text('Words')),
              const PopupMenuItem(value: 'sentence', child: Text('Sentences')),
              const PopupMenuItem(value: 'grammar', child: Text('Grammar')),
            ],
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _collections.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.folder_copy, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      Text(
                        _selectedType == null
                            ? 'No collections yet'
                            : 'No ${_getTypeLabel(_selectedType!)} collections',
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Create collections to organize your content',
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _collections.length,
                  itemBuilder: (context, index) {
                    final collection = _collections[index];
                    return _buildCollectionCard(collection);
                  },
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: _createCollection,
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildCollectionCard(Collection collection) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getTypeColor(collection.type),
          child: Icon(_getTypeIcon(collection.type), color: Colors.white),
        ),
        title: Text(
          collection.name,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text(_getTypeLabel(collection.type)),
        trailing: PopupMenuButton<String>(
          onSelected: (value) {
            if (value == 'edit') {
              _editCollection(collection);
            } else if (value == 'delete') {
              _deleteCollection(collection);
            } else if (value == 'view') {
              _viewCollectionItems(collection);
            }
          },
          itemBuilder: (context) => [
            const PopupMenuItem(value: 'view', child: Text('View Items')),
            const PopupMenuItem(value: 'edit', child: Text('Edit')),
            const PopupMenuItem(
              value: 'delete',
              child: Text('Delete', style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
        onTap: () => _viewCollectionItems(collection),
      ),
    );
  }

  String _getTypeLabel(String type) {
    switch (type) {
      case 'deck':
        return 'Decks';
      case 'word':
        return 'Words';
      case 'sentence':
        return 'Sentences';
      case 'grammar':
        return 'Grammar';
      default:
        return type;
    }
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'deck':
        return Icons.style;
      case 'word':
        return Icons.text_fields;
      case 'sentence':
        return Icons.format_quote;
      case 'grammar':
        return Icons.menu_book;
      default:
        return Icons.folder;
    }
  }

  Color _getTypeColor(String type) {
    switch (type) {
      case 'deck':
        return Colors.teal;
      case 'word':
        return Colors.blue;
      case 'sentence':
        return Colors.purple;
      case 'grammar':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }
}
