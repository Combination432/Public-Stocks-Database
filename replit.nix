{ pkgs }: {
  deps = [
    pkgs.postgresql
    pkgs.redis
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.nodejs_20
    pkgs.nodePackages.npm
  ];
}
