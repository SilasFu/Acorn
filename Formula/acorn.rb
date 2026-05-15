class Acorn < Formula
  desc "AI coding environment optimizer — auto-detect, diagnose, and fix your project setup"
  homepage "https://github.com/SilasFu/Acorn"
  license "MIT"
  version "0.1.0"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/SilasFu/Acorn/releases/download/v#{version}/acorn-macos-arm64"
      sha256 "REPLACE_ME_ARM64"
    else
      url "https://github.com/SilasFu/Acorn/releases/download/v#{version}/acorn-macos-amd64"
      sha256 "REPLACE_ME_AMD64"
    end
  end

  on_linux do
    url "https://github.com/SilasFu/Acorn/releases/download/v#{version}/acorn-linux-amd64"
    sha256 "REPLACE_ME_LINUX"
  end

  on_windows do
    url "https://github.com/SilasFu/Acorn/releases/download/v#{version}/acorn-windows-amd64.exe"
    sha256 "REPLACE_ME_WINDOWS"
  end

  def install
    if OS.windows?
      bin.install "acorn-windows-amd64.exe" => "acorn.exe"
    else
      bin.install "acorn"
    end
  end

  test do
    system "#{bin}/acorn", "--help"
  end
end
