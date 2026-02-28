/// Suggestions Storage Service
/// 
/// Manages storage and retrieval of AI-generated suggestions in the database.
/// Suggestions are stored as JSON in various tables (sentence_explanations,
/// chat_messages, writing_sessions).

import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import '../models/suggestions.dart';
import 'database_helper.dart';

class SuggestionsService {
  final DatabaseHelper _db;
  
  SuggestionsService(this._db);
  
  /// Get the database instance
  Future<Database> get _database async => await _db.database;
  
  /// Store suggestions for a sentence explanation
  /// 
  /// Stores suggestions JSON in sentence_explanations.grammar_notes column
  /// (repurposing existing column for suggestions storage)
  Future<void> storeSentenceSuggestions(
    int sentenceExplanationId,
    Suggestions suggestions,
  ) async {
    final jsonString = suggestions.toJsonString();
    
    await _db.updateItem(
      'sentence_explanations',
      sentenceExplanationId,
      {'grammar_notes': jsonString},
    );
  }
  
  /// Retrieve suggestions for a sentence explanation
  /// 
  /// Reads suggestions JSON from sentence_explanations.grammar_notes column
  Future<Suggestions?> getSentenceSuggestions(int sentenceExplanationId) async {
    final db = await _database;
    
    final results = await db.query(
      'sentence_explanations',
      columns: ['grammar_notes'],
      where: 'id = ?',
      whereArgs: [sentenceExplanationId],
    );
    
    if (results.isEmpty) {
      return null;
    }
    
    final jsonString = results.first['grammar_notes'] as String?;
    
    if (jsonString == null || jsonString.isEmpty) {
      return null;
    }
    
    try {
      return Suggestions.fromJsonString(jsonString);
    } catch (e) {
      // Return null if JSON parsing fails
      return null;
    }
  }
  
  /// Store suggestions in chat message analysis
  /// 
  /// Stores suggestions JSON in chat_messages.analysis column
  Future<void> storeChatSuggestions(
    int messageId,
    Suggestions suggestions,
  ) async {
    final jsonString = suggestions.toJsonString();
    
    await _db.updateItem(
      'chat_messages',
      messageId,
      {'analysis': jsonString},
    );
  }
  
  /// Retrieve suggestions from chat message
  /// 
  /// Reads suggestions JSON from chat_messages.analysis column
  Future<Suggestions?> getChatSuggestions(int messageId) async {
    final db = await _database;
    
    final results = await db.query(
      'chat_messages',
      columns: ['analysis'],
      where: 'id = ?',
      whereArgs: [messageId],
    );
    
    if (results.isEmpty) {
      return null;
    }
    
    final jsonString = results.first['analysis'] as String?;
    
    if (jsonString == null || jsonString.isEmpty) {
      return null;
    }
    
    try {
      return Suggestions.fromJsonString(jsonString);
    } catch (e) {
      // Return null if JSON parsing fails
      return null;
    }
  }
  
  /// Store suggestions in writing session analysis
  /// 
  /// Stores suggestions JSON in writing_sessions.analysis column
  Future<void> storeWritingSuggestions(
    int sessionId,
    Suggestions suggestions,
  ) async {
    final jsonString = suggestions.toJsonString();
    
    await _db.updateItem(
      'writing_sessions',
      sessionId,
      {'analysis': jsonString},
    );
  }
  
  /// Retrieve suggestions from writing session
  /// 
  /// Reads suggestions JSON from writing_sessions.analysis column
  Future<Suggestions?> getWritingSuggestions(int sessionId) async {
    final db = await _database;
    
    final results = await db.query(
      'writing_sessions',
      columns: ['analysis'],
      where: 'id = ?',
      whereArgs: [sessionId],
    );
    
    if (results.isEmpty) {
      return null;
    }
    
    final jsonString = results.first['analysis'] as String?;
    
    if (jsonString == null || jsonString.isEmpty) {
      return null;
    }
    
    try {
      return Suggestions.fromJsonString(jsonString);
    } catch (e) {
      // Return null if JSON parsing fails
      return null;
    }
  }
}
