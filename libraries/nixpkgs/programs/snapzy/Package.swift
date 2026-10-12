// swift-tools-version: 6.2
import PackageDescription

let package = Package(
  name: "Snapzy",
  platforms: [.macOS(.v13)],
  dependencies: [
    .package(url: "https://github.com/groue/GRDB.swift.git", from: "7.0.0"),
    .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.8.1"),
    .package(url: "https://github.com/ainame/Swift-WebP.git", from: "0.6.0"),
  ],
  targets: [
    .executableTarget(
      name: "Snapzy",
      dependencies: [
        .product(name: "GRDB", package: "GRDB.swift"),
        .product(name: "Sparkle", package: "Sparkle"),
        .product(name: "WebP", package: "Swift-WebP"),
      ],
      path: "Snapzy",
      exclude: ["Resources", "SnapzyIcon.icon", "Snapzy.entitlements"],
      swiftSettings: [
        .swiftLanguageMode(.v5),
        .defaultIsolation(MainActor.self),
        .enableUpcomingFeature("NonisolatedNonsendingByDefault"),
        .enableUpcomingFeature("InferIsolatedConformances"),
        .enableUpcomingFeature("MemberImportVisibility"),
      ]
    ),
  ]
)
