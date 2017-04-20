FROM debian:jessie 

MAINTAINER Yannik Behr <y.behr@gns.cri.nz>

ENV WORK_DIR /usr/local/src/
ENV INSTALL_DIR /opt/seiscomp3


# Fix Debian  env
ENV DEBIAN_FRONTEND noninteractive
ENV INITRD No
ENV FAKE_CHROOT 1

# Setup sysop's user and group id
ENV USER_ID 1000
ENV GROUP_ID 1000

WORKDIR $WORK_DIR

RUN echo 'force-unsafe-io' | tee /etc/dpkg/dpkg.cfg.d/02apt-speedup \
    && echo 'DPkg::Post-Invoke {"/bin/rm -f /var/cache/apt/archives/*.deb || true";};' | tee /etc/apt/apt.conf.d/no-cache \
    && apt-get update \
    && apt-get dist-upgrade -y --no-install-recommends \
    && apt-get install -y \
    build-essential \
    festival \
    cmake \
    cmake-curses-gui \
    flex \
    g++ \
    libgfortran3 \
    libncurses5-dev \
    gfortran \
    git \
    libboost-dev \
    libboost-filesystem-dev \
    libboost-iostreams-dev \
    libboost-program-options-dev \
    libboost-regex-dev \
    libboost-thread-dev \
    libboost-system-dev \
    libboost-signals-dev \
    python \
    python2.7 \
    libpython2.7 \
    libpython2.7-dev \
    libqt4-dev \
    libsqlite3-dev \
    sqlite3 \
    python-twisted \
    libxml2 \
    libxml2-dev \
    openssh-server \
    openssl \
    libssl-dev \
    net-tools \
    vim \
    libfaketime \
    && git clone --depth=1 https://github.com/yannikbehr/seiscomp3.git \
    && mkdir -p $WORK_DIR/seiscomp3/build \
    && cd $WORK_DIR/seiscomp3/build \
    && cmake .. -DSC_GLOBAL_GUI=OFF -DSC_TRUNK_DB_MYSQL=OFF \
       -DSC_TRUNK_DB_POSTGRESQL=OFF -DSC_TRUNK_DB_SQLITE3=ON \
       -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR \
    && make -j $(grep -c processor /proc/cpuinfo) \
    && make install

WORKDIR /tmp
ADD sc3-files.tar.bz .

# Now install evscore plugin
RUN cp -r evscore $WORK_DIR/seiscomp3/src/sed/plugins/ \
    && cp CMakeLists.evscore $WORK_DIR/seiscomp3/src/sed/plugins/CMakeLists.txt \
    && cd $WORK_DIR/seiscomp3/build \
    && make -j $(grep -c processor /proc/cpuinfo) \
    && make install \
    && apt-get autoremove -y --purge \
    && apt-get clean 
#    && rm -rf /var/lib/apt/lists/* /var/tmp/* 

# Setup ssh access
RUN mkdir /var/run/sshd
RUN echo 'root:password' | chpasswd
RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' \
    -i /etc/pam.d/sshd

RUN groupadd --gid $GROUP_ID -r sysop && useradd -m -s /bin/bash --uid $USER_ID -r -g sysop sysop \
    && echo 'sysop:sysop' | chpasswd \
    && chown -R sysop:sysop $INSTALL_DIR

RUN cp -r seiscomp3 /home/sysop/.seiscomp3 \
    && chown -R sysop:sysop /home/sysop/.seiscomp3 

USER sysop

### SeisComp3 settings ###
ENV SEISCOMP_ROOT=/opt/seiscomp3 PATH=/opt/seiscomp3/bin:$PATH \
    LD_LIBRARY_PATH=/opt/seiscomp3/lib:$LD_LIBRARY_PATH \
    PYTHONPATH=/opt/seiscomp3/lib/python:$PYTHONPATH \
    MANPATH=/opt/seiscomp3/share/man:$MANPATH \
    LC_ALL=C

# Setup SeisComP3 + seedlink
RUN seiscomp --stdin setup <sc3_config.cfg \
    && mkdir -p /opt/seiscomp3/var/lib/seedlink \
    && cp seedlink.ini /opt/seiscomp3/var/lib/seedlink/ \
    && mkdir -p /opt/seiscomp3/var/run/seedlink \
    && mkfifo -m=666 /opt/seiscomp3/var/run/seedlink/mseedfifo

# Setup pipelines
RUN seiscomp alias create NLoB_amp scamp \
    && seiscomp alias create NLoB_apick scautopick \
    && seiscomp alias create NLoB_auloc scautoloc \
    && seiscomp alias create NLoB_mag scmag \
    && seiscomp alias create NTeT_amp scamp \
    && seiscomp alias create NTeT_apick scautopick \
    && seiscomp alias create NTeT_auloc scautoloc \
    && seiscomp alias create NTeT_mag scmag \
    && seiscomp enable scevent scautopick scautoloc scmag scamp seedlink NLoB_amp \
    NLoB_apick NLoB_auloc NLoB_mag NTeT_amp NTeT_apick NTeT_auloc NTeT_mag

WORKDIR /home/sysop

VOLUME ["/home/sysop/data"]
VOLUME ["/home/sysop/sc3-playback"]

USER root
    
EXPOSE 22

# Start sshd
CMD ["/usr/sbin/sshd", "-D"]



