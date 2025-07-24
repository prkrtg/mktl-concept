#!/bin/bash
set -e

# Customize this if you're using Intel macOS
INSTALL_PREFIX=${INSTALL_PREFIX:-/opt/homebrew}

echo "Using install prefix: $INSTALL_PREFIX"
export CFLAGS="-I${INSTALL_PREFIX}/include"
export LDFLAGS="-L${INSTALL_PREFIX}/lib"
export PKG_CONFIG_PATH="${INSTALL_PREFIX}/lib/pkgconfig"

# Parallel jobs
NUM_CORES=$(sysctl -n hw.ncpu)

mkdir -p build_zyre
cd build_zyre

#########################################
# Build and install libzmq (via CMake)
#########################################
echo "Cloning libzmq..."
git clone https://github.com/zeromq/libzmq.git
cd libzmq
mkdir build && cd build
echo "Building libzmq..."
cmake .. -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX}
make -j${NUM_CORES}
sudo make install
cd ../..

#########################################
# Build and install czmq (via Autotools)
#########################################
echo "Cloning czmq..."
git clone https://github.com/zeromq/czmq.git
cd czmq
./autogen.sh
./configure --prefix=${INSTALL_PREFIX}
make -j${NUM_CORES}
sudo make install
cd ..

#########################################
# Build and install zyre (via Autotools)
#########################################
echo "Cloning zyre..."
git clone https://github.com/zeromq/zyre.git
cd zyre
./autogen.sh
./configure --prefix=${INSTALL_PREFIX}
make -j${NUM_CORES}
sudo make install
cd ..

echo "✅ All libraries built and installed successfully!"

