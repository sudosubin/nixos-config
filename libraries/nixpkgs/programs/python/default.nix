final: prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      cherrypy = (import ./cherrypy self super);
      poetry = (import ./poetry self super);
      pyopenssl = (import ./pyopenssl self super);
    };
  };
}
