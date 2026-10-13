{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.clop;

in
{
  options.services.clop = {
    enable = lib.mkEnableOption "clop";

    package = lib.mkPackageOption pkgs "clop" { };

    config = {
      adaptiveImageSize = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Adaptive image size";
      };

      adaptiveVideoSize = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Adaptive video size";
      };

      allowClopToAppearInScreenshots = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Show Clop UI in screenshots";
      };

      alwaysShowCompactResults = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Always use compact layout";
      };

      appendClipboardResults = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Keep all clipboard results";
      };

      audioBitrate = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Audio bitrate";
      };

      audioCoverArt = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "optimise"
            "remove"
            "keep"
          ]
        );
        default = null;
        description = "Cover art";
      };

      audioDirs = lib.mkOption {
        type = lib.types.nullOr (lib.types.listOf lib.types.str);
        default = null;
        description = "Audio dirs";
      };

      audioFormat = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "sameAsInput"
            "aac"
            "mp3"
            "opus"
            "wav"
            "flac"
            "aiff"
          ]
        );
        default = null;
        description = "Audio format";
      };

      autoClearAllCompactResultsAfter = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Auto clear all compact results after";
      };

      autoCopyToClipboard = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Auto Copy optimised files to clipboard";
      };

      autoHideClipboardResultAfter = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Auto hide clipboard results after";
      };

      autoHideFloatingResults = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Auto hide floating results";
      };

      autoHideFloatingResultsAfter = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Auto hide file results after";
      };

      batchModeFileCountThreshold = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Batch mode file threshold";
      };

      capVideoFPS = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Cap frames per second";
      };

      clipboardAccumulationTimeout = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Accumulation timeout";
      };

      clipboardIgnoredAppBundleIds = lib.mkOption {
        type = lib.types.nullOr (lib.types.listOf lib.types.str);
        default = null;
        description = "Clipboard ignored app bundle ids";
      };

      convertAudioToAAC = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Convert audio to AAC";
      };

      convertHDRToSDR = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Convert HDR to SDR";
      };

      convertedAudioBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Auto-conversion behaviour for compatible formats";
      };

      convertedImageBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Auto-conversion behaviour for compatible formats";
      };

      convertedSameFolderNameTemplateAudio = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Converted audio name template";
      };

      convertedSameFolderNameTemplateImage = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Converted file name template for Same folder as original";
      };

      convertedSameFolderNameTemplateVideo = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Name template for converted videos saved in the same folder";
      };

      convertedSpecificFolderNameTemplateAudio = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Converted audio path template";
      };

      convertedSpecificFolderNameTemplateImage = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Converted file path template for Specific folder";
      };

      convertedSpecificFolderNameTemplateVideo = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Path template for converted videos saved in a specific folder";
      };

      convertedVideoBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Auto-conversion behaviour for compatible formats";
      };

      copyConsecutiveClipboardImages = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Accumulate optimised images in clipboard";
      };

      copyImageFilePath = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Copy image paths";
      };

      customNameTemplateForClipboardImages = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Name template for clipboard images";
      };

      defaultLinkExpiration = lib.mkOption {
        type = lib.types.nullOr lib.types.number;
        default = null;
        description = "Default link expiration";
      };

      dirsHideFloatingResult = lib.mkOption {
        type = lib.types.nullOr (lib.types.listOf lib.types.str);
        default = null;
        description = "Dirs hide floating result";
      };

      dismissCompactResultOnDrop = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Dismiss compact result on drag and drop outside";
      };

      dismissCompactResultOnUpload = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Dismiss compact result on upload to Dropshare";
      };

      dismissFloatingResultOnDrop = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Dismiss result on drag and drop outside";
      };

      dismissFloatingResultOnUpload = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Dismiss result on upload to Dropshare";
      };

      editorAppAudio = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Audio";
      };

      editorAppImage = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Images";
      };

      editorAppPDF = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "PDFs";
      };

      editorAppVideo = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Videos";
      };

      enableAutomaticAudioOptimisations = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable **audio** auto-optimiser";
      };

      enableAutomaticImageOptimisations = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable image auto-optimiser";
      };

      enableAutomaticPDFOptimisations = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable PDF auto-optimiser";
      };

      enableAutomaticVideoOptimisations = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable video auto-optimiser";
      };

      enableClipboardOptimiser = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable clipboard optimiser";
      };

      enableDragAndDrop = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Enable drop zone";
      };

      enableFloatingResults = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Show floating results";
      };

      enablePhotosIntegration = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Optimise images copied from Photos.app";
      };

      finishedOnboarding = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Finished onboarding";
      };

      floatingResultsCorner = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "bottomLeft"
            "bottomRight"
            "topLeft"
            "topRight"
          ]
        );
        default = null;
        description = "Position on screen";
      };

      followCursorScreen = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Follow the cursor across screens";
      };

      formatPickerStyle = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "bar"
            "extensionHover"
          ]
        );
        default = null;
        description = "Change format by";
      };

      gifFrameDropBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "playFaster"
            "keepDuration"
          ]
        );
        default = null;
        description = "GIF frame dropping";
      };

      hideFloatingResultTooltips = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Hide button tooltips";
      };

      imageDirs = lib.mkOption {
        type = lib.types.nullOr (lib.types.listOf lib.types.str);
        default = null;
        description = "Image dirs";
      };

      manualConvertedAudioBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Manual conversion behaviour";
      };

      manualConvertedImageBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Manual conversion behaviour";
      };

      manualConvertedVideoBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Manual conversion behaviour";
      };

      maxAudioFileCount = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File count";
      };

      maxAudioSizeMB = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File size";
      };

      maxCopiedPhotosCount = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File count";
      };

      maxImageFileCount = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File count";
      };

      maxImageResolution = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Resolution";
      };

      maxImageSizeMB = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File size";
      };

      maxPDFFileCount = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File count";
      };

      maxPDFSizeMB = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File size";
      };

      maxPhotosLength = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Downscale to";
      };

      maxVideoFileCount = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File count";
      };

      maxVideoResolution = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Resolution";
      };

      maxVideoSizeMB = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File size";
      };

      mcpAllowScriptSteps = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Allow agents to write script steps";
      };

      mcpEnabled = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Accept changes from agents";
      };

      minAudioSizeKB = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File size";
      };

      minImageResolution = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Resolution";
      };

      minImageSizeKB = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File size";
      };

      minPDFSizeKB = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File size";
      };

      minVideoFPS = lib.mkOption {
        type = lib.types.nullOr lib.types.number;
        default = null;
        description = "but no less than";
      };

      minVideoResolution = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Resolution";
      };

      minVideoSizeKB = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "File size";
      };

      neverShowProError = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Never show pro error";
      };

      onlyShowDropZoneOnOption = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Require pressing ⌥ Option to show drop zone";
      };

      onlyShowPresetZonesOnControlTapped = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Show preset zones by holding or tapping Control";
      };

      optimiseAudioClipboard = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Audio files";
      };

      optimiseHEICAVIFClipboard = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "HEIC and AVIF data";
      };

      optimiseImagePathClipboard = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Image files";
      };

      optimisePDFClipboard = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "PDF files";
      };

      optimiseTIFF = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "TIFF data";
      };

      optimiseVideoClipboard = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Video files";
      };

      optimisedAudioBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Optimised file placement";
      };

      optimisedFileProtectionMs = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Re-optimisation loop detection window";
      };

      optimisedImageBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Optimised file placement";
      };

      optimisedPDFBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Optimised file placement";
      };

      optimisedVideoBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "temporary"
            "inPlace"
            "sameFolder"
            "specificFolder"
          ]
        );
        default = null;
        description = "Optimised file placement";
      };

      pauseAutomaticOptimisations = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Pause automatic optimisations";
      };

      pdfDPI = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Compression";
      };

      pdfDirs = lib.mkOption {
        type = lib.types.nullOr (lib.types.listOf lib.types.str);
        default = null;
        description = "Pdf dirs";
      };

      photoCropOrientation = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "landscape"
            "portrait"
            "adaptive"
          ]
        );
        default = null;
        description = "Photos crop orientation";
      };

      playbackSpeedFrameBehaviour = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "keepFrames"
            "dropFrames"
          ]
        );
        default = null;
        description = "Playback speed change";
      };

      preserveColorMetadata = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Preserve color profile metadata";
      };

      preserveDates = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Preserve file creation and modification dates";
      };

      removeAudioFromVideos = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Remove audio on optimised videos";
      };

      sameFolderNameTemplateAudio = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Optimised audio name template";
      };

      sameFolderNameTemplateImage = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Name template for Same folder as original";
      };

      sameFolderNameTemplatePDF = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Same folder name template";
      };

      sameFolderNameTemplateVideo = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Name template for optimised videos saved in the same folder";
      };

      showCompactImages = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Show images in compact results";
      };

      showCopyClearButtons = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Show Copy all and Clear all buttons";
      };

      showMenubarIcon = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Menubar icon";
      };

      specificFolderNameTemplateAudio = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Optimised audio path template";
      };

      specificFolderNameTemplateImage = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Path template for Specific folder";
      };

      specificFolderNameTemplatePDF = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Specific folder name template";
      };

      specificFolderNameTemplateVideo = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Path template for optimised videos saved in a specific folder";
      };

      stripMetadata = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Strip EXIF Metadata";
      };

      syncSettingsCloud = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Sync settings with other Macs via iCloud";
      };

      targetVideoFPS = lib.mkOption {
        type = lib.types.nullOr lib.types.number;
        default = null;
        description = "Cap frames per second";
      };

      useAggressiveOptimisationGIF = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Use aggressive optimisation g i f";
      };

      useAggressiveOptimisationJPEG = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Use aggressive optimisation j p e g";
      };

      useAggressiveOptimisationMP4 = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Use aggressive optimisation m p4";
      };

      useAggressiveOptimisationPNG = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Use aggressive optimisation p n g";
      };

      useBatchModeForFolders = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Use batch mode for large drops";
      };

      useCPUIntensiveEncoder = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Use c p u intensive encoder";
      };

      useClassicMenubarIcon = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Menubar icon";
      };

      useCustomNameTemplateForClipboardImages = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Use a name template for clipboard images";
      };

      useGeometricMenubarIcon = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Menubar icon";
      };

      videoDirs = lib.mkOption {
        type = lib.types.nullOr (lib.types.listOf lib.types.str);
        default = null;
        description = "Video dirs";
      };

      videoEncoder = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            "fast"
            "slowHighQuality"
            "visuallyLossless"
          ]
        );
        default = null;
        description = "Video encoder";
      };

      workdir = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Working directory path";
      };

      workdirCleanupInterval = lib.mkOption {
        type = lib.types.nullOr (
          lib.types.enum [
            0
            600
            3600
            43200
            86400
            259200
            604800
            2592000
          ]
        );
        default = null;
        description = "Working directory cleanup";
      };
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix clop only supports darwin.";
        }
        {
          assertion = cfg.enable -> config.targets.darwin.copyApps.enable;
          message = "services.clop requires targets.darwin.copyApps.enable.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];

      targets.darwin.defaults."com.lowtechguys.Clop" = cfg.config;

      launchd.agents.clop = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/${config.targets.darwin.copyApps.directory}/Clop.app/Contents/MacOS/Clop"
          ];
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/clop.log";
          StandardErrorPath = "${config.xdg.cacheHome}/clop.log";
        };
      };
    })
  ];
}
