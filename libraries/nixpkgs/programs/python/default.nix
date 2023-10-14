final: prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      cherrypy = (import ./cherrypy.nix self super);
    };
  };
}
