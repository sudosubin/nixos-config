// swift-tools-version: 6.0
import PackageDescription

let package = Package(
  name: "DeskPad",
  platforms: [.macOS(.v13)],
  dependencies: [
    .package(url: "https://github.com/ReSwift/ReSwift.git", from: "6.0.0"),
  ],
  targets: [
    .executableTarget(
      name: "DeskPad",
      dependencies: [
        .product(name: "ReSwift", package: "ReSwift"),
      ],
      path: "DeskPad",
      exclude: [
        "Assets.xcassets",
        "CGVirtualDisplayPrivate.h",
        "DeskPad-Bridging-Header.h",
        "DeskPad.entitlements",
      ],
      swiftSettings: [
        .swiftLanguageMode(.v5),
        // SWIFT_OBJC_BRIDGING_HEADER
        .unsafeFlags(["-import-objc-header", "DeskPad/DeskPad-Bridging-Header.h"]),
      ]
    ),
  ]
)
