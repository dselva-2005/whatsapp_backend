import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'api_service.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: QRScannerPage(),
    );
  }
}

class QRScannerPage extends StatefulWidget {
  const QRScannerPage({super.key});

  @override
  State<QRScannerPage> createState() => _QRScannerPageState();
}

class _QRScannerPageState extends State<QRScannerPage> {
  final MobileScannerController controller = MobileScannerController();

  bool scanned = false;
  bool loading = false;

  String? phone;
  Map<String, dynamic>? userData;

  Future<void> handleScan(String value) async {
    if (scanned) return;

    scanned = true;
    controller.stop();

    setState(() {
      loading = true;
      phone = value;
    });

    final data = await ApiService.getStatus(value);

    setState(() {
      userData = data;
      loading = false;
    });
  }

  Future<void> redeem() async {
    if (phone == null) return;

    setState(() => loading = true);

    final result = await ApiService.redeem(phone!);
    final updated = await ApiService.getStatus(phone!);

    setState(() {
      userData = updated;
      loading = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(result["status"])),
    );
  }

  void resetScanner() {
    setState(() {
      scanned = false;
      phone = null;
      userData = null;
    });
    controller.start();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("QR Scanner"),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: resetScanner,
          )
        ],
      ),
      body: Column(
        children: [
          Expanded(
            flex: 3,
            child: MobileScanner(
              controller: controller,
              onDetect: (capture) {
                final value = capture.barcodes.first.rawValue;
                if (value != null) {
                  handleScan(value);
                }
              },
            ),
          ),
          Expanded(
            flex: 2,
            child: Center(
              child: loading
                  ? const CircularProgressIndicator()
                  : userData == null
                      ? const Text("Scan a QR code")
                      : UserStatusCard(
                          data: userData!,
                          onRedeem: redeem,
                        ),
            ),
          ),
        ],
      ),
    );
  }
}

/* =========================
   USER STATUS CARD
========================= */

class UserStatusCard extends StatelessWidget {
  final Map<String, dynamic> data;
  final VoidCallback onRedeem;

  const UserStatusCard({
    super.key,
    required this.data,
    required this.onRedeem,
  });

  String formatTimestamp(String isoString) {
    final dateTime = DateTime.parse(isoString).toLocal();
    return "${dateTime.day.toString().padLeft(2, '0')}-"
        "${dateTime.month.toString().padLeft(2, '0')}-"
        "${dateTime.year}  "
        "${dateTime.hour.toString().padLeft(2, '0')}:"
        "${dateTime.minute.toString().padLeft(2, '0')}";
  }

  @override
  Widget build(BuildContext context) {
    final canRedeem = data["can_redeem"] == true;
    final redeemedAt = data["redeemed_at"];

    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text("Phone: ${data["phone"] ?? "-"}"),
            Text("Name: ${data["name"] ?? "-"}"),
            Text("State: ${data["state"] ?? "-"}"),

            if (redeemedAt != null) ...[
              const SizedBox(height: 8),
              Text(
                "Redeemed at: ${formatTimestamp(redeemedAt)}",
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  color: Colors.green,
                ),
              ),
            ],

            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: canRedeem ? onRedeem : null,
              child: const Text("Offer Redeem"),
            ),
          ],
        ),
      ),
    );
  }
}
