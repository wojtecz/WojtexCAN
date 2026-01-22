#include <SPI.h>
#include <mcp2515.h>

MCP2515 mcp2515(10);
int temp = -1;

struct can_frame rxMsg;

void setup() {
  Serial.begin(115200);
  SPI.begin();

  mcp2515.reset();
  mcp2515.setBitrate(CAN_100KBPS);
  mcp2515.setNormalMode();
}

void loop() {
  // ODBIÓR Z UART (wysyłanie CAN)
  if (Serial.available()) {
    String input = Serial.readStringUntil('A');
    input.trim();

    if (input.length() > 30) {
      ramka(input);
    }
  }

  // ODBIÓR Z CAN (wysyłanie do PC)
  if (mcp2515.readMessage(&rxMsg) == MCP2515::ERROR_OK) {
    Serial.print("R;");
    Serial.print(rxMsg.can_id);
    Serial.print(";");
    Serial.print(rxMsg.can_dlc);

    for (int i = 0; i < rxMsg.can_dlc; i++) {
      Serial.print(";");
      Serial.print(rxMsg.data[i]);
    }
    Serial.println();
  }
}

void ramka(String dane) {
  if (dane.charAt(0) == '1') {
    struct can_frame canMsg;

    canMsg.can_dlc = 8;
    canMsg.can_id = dane.substring(3, 7).toInt();

    predkosc(dane.substring(1, 3));

    for (int i = 0; i < 8; i++) {
      canMsg.data[i] = dane.substring(i * 3 + 7, i * 3 + 10).toInt();
    }

    mcp2515.sendMessage(&canMsg);
  }
}

void predkosc(String dane) {
  if (temp != dane.toInt()) {
    mcp2515.reset();
    temp = dane.toInt();

    switch (temp) {
      case 1: mcp2515.setBitrate(CAN_5KBPS); break;
      case 2: mcp2515.setBitrate(CAN_10KBPS); break;
      case 3: mcp2515.setBitrate(CAN_20KBPS); break;
      case 4: mcp2515.setBitrate(CAN_31K25BPS); break;
      case 5: mcp2515.setBitrate(CAN_33KBPS); break;
      case 6: mcp2515.setBitrate(CAN_40KBPS); break;
      case 7: mcp2515.setBitrate(CAN_50KBPS); break;
      case 8: mcp2515.setBitrate(CAN_80KBPS); break;
      case 9: mcp2515.setBitrate(CAN_83K3BPS); break;
      case 10: mcp2515.setBitrate(CAN_95KBPS); break;
      case 11: mcp2515.setBitrate(CAN_100KBPS); break;
      case 12: mcp2515.setBitrate(CAN_125KBPS); break;
      case 13: mcp2515.setBitrate(CAN_200KBPS); break;
      case 14: mcp2515.setBitrate(CAN_250KBPS); break;
      case 15: mcp2515.setBitrate(CAN_500KBPS); break;
      case 16: mcp2515.setBitrate(CAN_1000KBPS); break;
    }
    mcp2515.setNormalMode();
  }
}
