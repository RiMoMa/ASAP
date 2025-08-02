#!/bin/bash
# Build ASAP and produce a universal package for Linux.
# Usage: build_universal_package.sh [build_gui] [package_type]
# - build_gui: "true" (default) or "false"
# - package_type: DEB or TGZ (default TGZ)

build_gui="${1:-true}"
package_type="${2:-TGZ}"

echo "Building ASAP; build_gui=${build_gui}; package_type=${package_type}"

git clone https://github.com/computationalpathologygroup/ASAP src
mkdir build
cd build || exit

cmake_common_args=(
  -DWRAP_MULTIRESOLUTIONIMAGEINTERFACE_PYTHON=TRUE
  -DCMAKE_INSTALL_PREFIX=/root/install
  -DPACKAGE_ON_INSTALL=TRUE
  -DSWIG_EXECUTABLE=/root/swig/install/bin/swig
  -DPython3_ROOT_DIR=/root/miniconda3/envs/build
  -DCPACK_GENERATOR="${package_type}"
)

if [ "${build_gui}" = "true" ]; then
  cmake ../src \
    -DOPENSLIDE_INCLUDE_DIR=/usr/local/include/openslide \
    -DOpenJPEG_DIR=/root/openjpeg/install/lib/cmake/openjpeg-2.5 \
    -DBUILD_ASAP=TRUE -DBUILD_EXECUTABLES=TRUE -DBUILD_IMAGEPROCESSING=TRUE \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_WORKLIST_INTERFACE=TRUE \
    -DQt6_DIR=/root/qt/6.5.2/gcc_64/lib/cmake/Qt6 \
    -DQt6GuiTools_DIR=/root/qt/6.5.2/gcc_64/lib/cmake/Qt6GuiTools \
    "${cmake_common_args[@]}"
else
  echo "Skipping GUI..."
  cmake ../src \
    -DOPENSLIDE_INCLUDE_DIR=/usr/include/openslide \
    -DOpenJPEG_DIR=/root/openjpeg/install/lib/cmake/openjpeg-2.5 \
    -DCMAKE_BUILD_TYPE=Release \
    "${cmake_common_args[@]}"
fi

export LD_LIBRARY_PATH=/root/miniconda3/envs/build/lib
make package

output_ext="tar.gz"
[ "${package_type}" = "DEB" ] && output_ext="deb"

mkdir -p /artifacts
for file in *."${output_ext}"; do
  if [ "${build_gui}" = "true" ]; then
    cp "$file" "/artifacts/${file%.*}-Linux.${output_ext}"
  else
    cp "$file" "/artifacts/${file%.*}-nogui-Linux.${output_ext}"
  fi
done
