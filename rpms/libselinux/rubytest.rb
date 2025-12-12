require 'selinux'
print "selinux\n"
print "Is selinux enabled? " + Selinux.is_selinux_enabled().to_s + "\n"
print "Is selinux enforce? " + Selinux.security_getenforce().to_s + "\n"
print "Setfscreatecon? " + Selinux.setfscreatecon("system_u:object_r:etc_t:s0").to_s + "\n"
print "/etc -> " + Selinux.matchpathcon("/etc", 0)[1] + "\n"
