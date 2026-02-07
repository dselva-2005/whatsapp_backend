import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Emulator → host machine
  static const String baseUrl = "https://allspray.in";

  static Future<Map<String, dynamic>> getStatus(String phone) async {
    final response = await http.get(
      Uri.parse("$baseUrl/api/qr/status/$phone"),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      return {
        "status": "error",
        "message": "User not found"
      };
    }
  }

  static Future<Map<String, dynamic>> redeem(String phone) async {
    final response = await http.post(
      Uri.parse("$baseUrl/api/qr/redeem/$phone"),
    );

    return jsonDecode(response.body);
  }
}
