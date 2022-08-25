self: super:

super.debugpy.overridePythonAttrs (attrs: {
  disabledTests = [
    "test_django"
    "test_flask"
  ];
})
