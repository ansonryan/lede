include $(TOPDIR)/rules.mk

PKG_NAME:=pcat-manager
PKG_VERSION:=2.0.0
PKG_RELEASE:=46

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/photonicat/rockchip_rk3568_pcat_manager
PKG_SOURCE_DATE:=2026-03-20
PKG_SOURCE_VERSION:=961edb8b5cbae63efb03ee774d198f6fdb682a45

PKG_LICENSE:=GPL-3.0
PKG_LICENSE_FILES:=LICENSE

PKG_INSTALL:=1
PKG_USE_MIPS16:=0

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/nls.mk
include $(INCLUDE_DIR)/meson.mk

define Package/pcat-manager
  SECTION:=utils
  CATEGORY:=Utilities
  DEPENDS:=+glib2 +libjson-c +libusb-1.0
  TITLE:=PCat System Manager
  URL:=https://git.g77k.com
  PROVIDES:=pcat-manager
endef

define Package/pcat-manager/description
  PCat Manager is a system service for power management and modem controlling.
endef

define Package/pcat-manager/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) \
		$(PKG_INSTALL_DIR)/usr/bin/pcat-manager \
		$(1)/usr/bin/pcat-manager

	$(INSTALL_BIN) \
		$(PKG_INSTALL_DIR)/usr/bin/pcat-pmu-updater \
		$(1)/usr/bin/pcat-pmu-updater

	$(INSTALL_BIN) \
		$(PKG_BUILD_DIR)/src/fm350-mm.py \
		$(1)/usr/bin/fm350-mm.py


	$(INSTALL_DIR) $(1)/etc

	$(INSTALL_CONF) ./files/pcat-manager.conf $(1)/etc

	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/pcat-manager.init $(1)/etc/init.d/pcat-manager
endef


$(eval $(call BuildPackage,pcat-manager))
