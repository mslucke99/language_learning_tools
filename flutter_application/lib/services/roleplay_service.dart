import 'dart:convert';
import 'package:proficiency_suites/models/models.dart';
import 'package:proficiency_suites/services/database_helper.dart';

class RoleplayService {
  final DatabaseHelper _db = DatabaseHelper();

  /// Get all roleplay scenarios
  Future<List<RoleplayScenario>> getScenarios() async {
    final db = await _db.database;
    
    final result = await db.query(
      'roleplay_scenarios',
      where: 'deleted_at IS NULL',
      orderBy: 'name ASC',
    );

    return result.map((json) => RoleplayScenario.fromJson(json)).toList();
  }

  /// Get a single roleplay scenario
  Future<RoleplayScenario?> getScenario(int scenarioId) async {
    final db = await _db.database;
    
    final result = await db.query(
      'roleplay_scenarios',
      where: 'id = ? AND deleted_at IS NULL',
      whereArgs: [scenarioId],
    );

    if (result.isEmpty) return null;
    return RoleplayScenario.fromJson(result.first);
  }

  /// Start a roleplay chat session
  Future<int> startRoleplaySession(
    int scenarioId,
    String language,
  ) async {
    final scenario = await getScenario(scenarioId);
    if (scenario == null) {
      throw Exception('Scenario not found');
    }

    final now = DateTime.now().toIso8601String();
    
    return await _db.insertItem('chat_sessions', {
      'mode': 'roleplay',
      'scenario_id': scenarioId,
      'study_language': language,
      'character_context': scenario.characters,
      'cur_topic': scenario.name,
      'created_at': now,
      'last_updated': now,
    });
  }

  /// Parse characters from JSON string
  List<Map<String, dynamic>> parseCharacters(String charactersJson) {
    try {
      final decoded = json.decode(charactersJson);
      if (decoded is List) {
        return decoded.cast<Map<String, dynamic>>();
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  /// Get character names from scenario
  List<String> getCharacterNames(RoleplayScenario scenario) {
    final characters = parseCharacters(scenario.characters);
    return characters.map((c) => c['name'] as String? ?? 'Unknown').toList();
  }

  /// Get character details
  Map<String, dynamic>? getCharacterByName(
    RoleplayScenario scenario,
    String name,
  ) {
    final characters = parseCharacters(scenario.characters);
    try {
      return characters.firstWhere((c) => c['name'] == name);
    } catch (e) {
      return null;
    }
  }

  /// Create a new roleplay scenario (for future use)
  Future<int> createScenario({
    required String name,
    String? description,
    required String userRole,
    required String situation,
    required List<Map<String, dynamic>> characters,
  }) async {
    final now = DateTime.now().toIso8601String();
    
    return await _db.insertItem('roleplay_scenarios', {
      'name': name,
      'description': description,
      'user_role': userRole,
      'situation': situation,
      'characters': json.encode(characters),
      'created_at': now,
      'last_updated': now,
    });
  }

  /// Update a roleplay scenario
  Future<void> updateScenario(
    int scenarioId, {
    String? name,
    String? description,
    String? userRole,
    String? situation,
    List<Map<String, dynamic>>? characters,
  }) async {
    final now = DateTime.now().toIso8601String();
    final Map<String, dynamic> updates = {'last_updated': now};
    
    if (name != null) updates['name'] = name;
    if (description != null) updates['description'] = description;
    if (userRole != null) updates['user_role'] = userRole;
    if (situation != null) updates['situation'] = situation;
    if (characters != null) updates['characters'] = json.encode(characters);
    
    await _db.updateItem('roleplay_scenarios', scenarioId, updates);
  }

  /// Delete a roleplay scenario
  Future<void> deleteScenario(int scenarioId) async {
    await _db.softDelete('roleplay_scenarios', scenarioId);
  }
}
