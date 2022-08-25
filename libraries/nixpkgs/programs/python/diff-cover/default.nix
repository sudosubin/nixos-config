self: super:

super.diff-cover.overridePythonAttrs (attrs: {
  disabledTests = (attrs.disabledTests or [ ]) ++ [
    # https://github.com/NixOS/nixpkgs/pull/187706
    "test_fail_under_console"
    "test_fail_under_pass_console"
    "test_added_file_pyflakes_console"
    "test_added_file_pyflakes_console_two_files"
  ];
})
