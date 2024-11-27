// Pin untuk encoder
const int encoderPinA = 2; // Pin untuk Encoder A
const int encoderPinB = 3; // Pin untuk Encoder B

// Pin untuk motor driver L298
const int motorPin1 = 8; // Pin untuk mengontrol arah motor
const int motorPin2 = 9; // Pin untuk mengontrol arah motor
const int pwmPin = 10;   // Pin untuk mengontrol kecepatan (PWM)

volatile int encoderCount = 0; // Menghitung jumlah pulse dari encoder
unsigned long lastTime = 0;    // Waktu terakhir pembaruan
float rpm = 0;                 // Kecepatan dalam RPM
float targetRpm = 0;           // Nilai RPM yang diset
char direction = 'S';          // Arah motor

// Variabel PID
float Kp = 0.5, Ki = 0.1, Kd = 0.1; // Parameter PID
float integral = 0, previousError = 0; // Variabel untuk PID
unsigned long lastPidTime = 0;        // Waktu terakhir PID

// Deklarasi fungsi
void countEncoder();

void setup() {
    Serial.begin(9600); // Inisialisasi serial monitor
    pinMode(encoderPinA, INPUT);
    pinMode(encoderPinB, INPUT);

    pinMode(motorPin1, OUTPUT);
    pinMode(motorPin2, OUTPUT);
    pinMode(pwmPin, OUTPUT);

    attachInterrupt(digitalPinToInterrupt(encoderPinA), countEncoder, RISING);
}

void loop() {
    unsigned long currentTime = millis();

    // Hitung kecepatan setiap 100 ms
    if (currentTime - lastTime >= 100) {
        rpm = (encoderCount / 124.8) * 600; // Hitung RPM (ganti 124.8 dengan jumlah pulse per putaran)
        encoderCount = 0;                  // Reset hitungan encoder
        lastTime = currentTime;            // Update waktu terakhir

        // Kirim data RPM dan arah melalui Serial
        Serial.print("RPM:");
        Serial.print(rpm);
        Serial.print(", Arah:");
        Serial.println(direction);
    }

    // Jalankan kontrol PID setiap 100 ms
    if (currentTime - lastPidTime >= 100) {
        float error = targetRpm - rpm; // Hitung error
        integral += error * 0.1;       // Hitung integral (0.1 = 100 ms)
        float derivative = (error - previousError) / 0.1; // Hitung turunan
        float output = Kp * error + Ki * integral + Kd * derivative; // PID output
        previousError = error;       // Simpan error sebelumnya
        lastPidTime = currentTime;   // Update waktu terakhir PID

        // Pastikan output berada di rentang 0-255 untuk PWM
        int pwmValue = constrain(output, 0, 255);
        WriteDriverVoltage(pwmValue);
    }

    // Proses input serial dari Python
    if (Serial.available() > 0) {
        String input = Serial.readStringUntil('\n'); // Baca input hingga newline
        if (input.startsWith("SET RPM")) {          // Contoh format: "SET RPM:1200"
            int delimiterIndex = input.indexOf(':');
            if (delimiterIndex > 0) {
                targetRpm = input.substring(delimiterIndex + 1).toFloat();
                Serial.print("Target RPM diatur menjadi: ");
                Serial.println(targetRpm);
            }
        } else if (input.startsWith("Arah")) {      // Contoh format: "Arah:Clockwise"
            int delimiterIndex = input.indexOf(':');
            if (delimiterIndex > 0) {
                String dir = input.substring(delimiterIndex + 1);
                if (dir == "Clockwise") {
                    direction = 'F';
                    digitalWrite(motorPin1, HIGH);
                    digitalWrite(motorPin2, LOW);
                } else if (dir == "Counterclockwise") {
                    direction = 'B';
                    digitalWrite(motorPin1, LOW);
                    digitalWrite(motorPin2, HIGH);
                }
                Serial.print("Arah motor diatur ke: ");
                Serial.println(dir);
            }
        }
    }
}

void countEncoder() {
    encoderCount++; // Increment jumlah pulse ketika encoder mendeteksi pulse
}

void WriteDriverVoltage(int pwmValue) {
    analogWrite(pwmPin, pwmValue); // Mengatur PWM ke motor
}