// swift-tools-version: 6.2
import PackageDescription

// SWIFT_DEFAULT_ACTOR_ISOLATION, SWIFT_APPROACHABLE_CONCURRENCY, SWIFT_UPCOMING_FEATURE_MEMBER_IMPORT_VISIBILITY
let concurrency: [SwiftSetting] = [
  .defaultIsolation(MainActor.self),
  .enableUpcomingFeature("NonisolatedNonsendingByDefault"),
  .enableUpcomingFeature("InferIsolatedConformances"),
  .enableUpcomingFeature("InferSendableFromCaptures"),
  .enableUpcomingFeature("DisableOutwardActorInference"),
  .enableUpcomingFeature("GlobalActorIsolatedTypesUsability"),
  .enableUpcomingFeature("MemberImportVisibility"),
]

let package = Package(
  name: "Hammerspoon 2",
  platforms: [.macOS(.v26)],
  dependencies: [
    .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.8.0"),
    .package(url: "https://github.com/cmsj/AXSwift", branch: "main"),
    .package(url: "https://github.com/cmsj/javascript-core-extras", branch: "main"),
    .package(url: "https://github.com/cmsj/swift-commandlinekit", branch: "master"),
  ],
  targets: [
    .target(
      name: "HSScreenPrivate",
      path: "Hammerspoon 2/Modules/hs.screen",
      sources: ["HSScreenPrivate.m"],
      publicHeadersPath: "."
    ),
    .executableTarget(
      name: "Hammerspoon 2",
      dependencies: [
        "HSScreenPrivate",
        .product(name: "Sparkle", package: "Sparkle"),
        .product(name: "AXSwift", package: "AXSwift"),
        .product(name: "JavaScriptCoreExtras", package: "javascript-core-extras"),
      ],
      path: "Hammerspoon 2",
      exclude: [
        "AppIcon.icon",
        "Assets.xcassets",
        "Bridging-Header.h",
        "Modules/hs.midi_/README_FOLDER_NAME.md",
        "Modules/hs.screen/HSScreenPrivate.h",
        "Modules/hs.screen/HSScreenPrivate.m",
      ],
      swiftSettings: concurrency + [
        .swiftLanguageMode(.v6),
        .strictMemorySafety(),
        .unsafeFlags([
          // SWIFT_OBJC_BRIDGING_HEADER
          "-import-objc-header", "Hammerspoon 2/Bridging-Header.h",
          // `import AVKit` implies _AVKit_SwiftUI (VideoPlayer) in Xcode
          "-Xfrontend", "-enable-cross-import-overlays",
        ]),
      ],
      linkerSettings: [
        .linkedFramework("AVKit"),
        .linkedFramework("ScriptingBridge"),
      ]
    ),
    .executableTarget(
      name: "HammerspoonOSAScriptHelper",
      path: "HammerspoonOSAScriptHelper",
      exclude: ["Info.plist"],
      swiftSettings: concurrency + [
        .swiftLanguageMode(.v5),
        .enableExperimentalFeature("StrictConcurrency=complete"),
      ]
    ),
    .executableTarget(
      name: "hs2",
      dependencies: [
        .product(name: "CommandLineKit", package: "swift-commandlinekit"),
      ],
      path: "hs2",
      swiftSettings: concurrency + [
        .swiftLanguageMode(.v6),
        .strictMemorySafety(),
      ]
    ),
  ]
)
