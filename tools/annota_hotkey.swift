import Foundation
import Carbon.HIToolbox

let keyCodes: [String: UInt32] = [
    "A": 0, "S": 1, "D": 2, "F": 3, "H": 4, "G": 5, "Z": 6, "X": 7,
    "C": 8, "V": 9, "B": 11, "Q": 12, "W": 13, "E": 14, "R": 15,
    "Y": 16, "T": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22,
    "5": 23, "9": 25, "7": 26, "8": 28, "0": 29, "O": 31, "U": 32,
    "I": 34, "P": 35, "L": 37, "J": 38, "K": 40, "N": 45, "M": 46,
    "F1": 122, "F2": 120, "F3": 99, "F4": 118, "F5": 96, "F6": 97,
    "F7": 98, "F8": 100, "F9": 101, "F10": 109, "F11": 103, "F12": 111,
    "F13": 105, "F14": 107, "F15": 113, "F16": 106, "F17": 64,
    "F18": 79, "F19": 80, "F20": 90
]

func fail(_ message: String, code: Int32 = 2) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(code)
}

guard CommandLine.arguments.count >= 2 else {
    fail("ERROR missing shortcut")
}

let shortcut = CommandLine.arguments[1]
let parts = shortcut.split(separator: "+").map { String($0).trimmingCharacters(in: .whitespaces) }
guard parts.count >= 2 else {
    fail("ERROR invalid shortcut: \(shortcut)")
}

let keyName = parts.last!.uppercased()
guard let keyCode = keyCodes[keyName] else {
    fail("ERROR unsupported key: \(keyName)")
}

var modifiers: UInt32 = 0
for raw in parts.dropLast() {
    switch raw.lowercased() {
    case "option", "alt": modifiers |= UInt32(optionKey)
    case "ctrl", "control": modifiers |= UInt32(controlKey)
    case "shift": modifiers |= UInt32(shiftKey)
    case "cmd", "command": modifiers |= UInt32(cmdKey)
    default: fail("ERROR unsupported modifier: \(raw)")
    }
}

func hotKeyHandler(
    _ nextHandler: EventHandlerCallRef?,
    _ event: EventRef?,
    _ userData: UnsafeMutableRawPointer?
) -> OSStatus {
    print("TRIGGER")
    fflush(stdout)
    return noErr
}

var eventType = EventTypeSpec(
    eventClass: OSType(kEventClassKeyboard),
    eventKind: UInt32(kEventHotKeyPressed)
)
var handlerRef: EventHandlerRef?
let handlerStatus = InstallEventHandler(
    GetApplicationEventTarget(),
    hotKeyHandler,
    1,
    &eventType,
    nil,
    &handlerRef
)
guard handlerStatus == noErr else {
    fail("ERROR InstallEventHandler status=\(handlerStatus)")
}

var hotKeyRef: EventHotKeyRef?
let hotKeyID = EventHotKeyID(signature: OSType(0x414E4E4F), id: 1) // ANNO
let registerStatus = RegisterEventHotKey(
    keyCode,
    modifiers,
    hotKeyID,
    GetApplicationEventTarget(),
    0,
    &hotKeyRef
)
guard registerStatus == noErr else {
    fail("ERROR RegisterEventHotKey status=\(registerStatus)")
}

print("READY \(shortcut)")
fflush(stdout)

while true {
    _ = RunCurrentEventLoop(1.0)
}
