self: super: {
  debugpy = super.debugpy.overridePythonAttrs (attrs: {
    disabledTests = [
      "test_django"
      "test_flask"
    ];
  });
}
