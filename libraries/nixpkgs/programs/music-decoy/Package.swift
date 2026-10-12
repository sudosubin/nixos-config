// swift-tools-version: 6.0
import PackageDescription

let package = Package(
  name: "Music Decoy",
  platforms: [.macOS(.v12)],
  targets: [
    .executableTarget(
      name: "Music Decoy",
      path: "Music",
      exclude: [
        "Assets.xcassets",
        "Base.lproj",
        "Info.plist",
        "MusicDecoy.sdef",
      ],
      linkerSettings: [
        .linkedFramework("Cocoa"),
        .linkedFramework("ServiceManagement"),
      ]
    ),
  ]
)
