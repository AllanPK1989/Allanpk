{{flutter_js}}
{{flutter_build_config}}

// Serve the CanvasKit renderer from our own origin instead of the Google CDN:
// one fewer third-party dependency, and it keeps working on networks that
// block gstatic.com. The files are copied into build/web/canvaskit/.
_flutter.loader.load({
  config: {
    canvasKitBaseUrl: "canvaskit/",
  },
});
