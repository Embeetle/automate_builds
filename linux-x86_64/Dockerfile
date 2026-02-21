# ~/embeetle_docker/Dockerfile

FROM quay.io/pypa/manylinux_2_34_x86_64:2026.02.01-1

# 1. Compatibility and base libraries
RUN yum -y install compat-openssl11 && yum -y clean all
RUN ldconfig && (ldconfig -p | grep -E 'libcrypto\.so\.1\.1|libssl\.so\.1\.1')

# 2. Build tools, UI, and Embeetle dependencies
# --> ADDED: p7zip
RUN yum -y install \
    cmake ninja-build gcc gcc-c++ make p7zip \
    libatomic atk cairo cairo-gobject cups gtk3 gstreamer1-plugins-base \
    mysql-libs unixODBC pcsc-lite-libs libpq pulseaudio-libs speech-dispatcher \
    libxcb rsync libxkbcommon libxkbcommon-x11 xcb-util-wm xcb-util-image \
    xcb-util-keysyms xcb-util-renderutil ncurses-compat-libs nss \
    libXcomposite libXdamage libXrandr libXtst alsa-lib.x86_64 \
    libxkbfile mesa-dri-drivers && \
    yum -y clean all

# 3. Python Virtual Environment Setup
ENV VIRTUAL_ENV=/opt/venv
RUN python3.13 -m venv --prompt Py3.13 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip

# 4. Working Directory
WORKDIR /root

# 5. Default command for manual debugging
CMD ["/bin/bash"]