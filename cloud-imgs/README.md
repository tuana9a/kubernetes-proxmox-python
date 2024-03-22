# cloud img and how to build them

cd into each dir and run the build.sh script

# Troubleshooting

[How to fix partition table after virt-resize rearranges it](https://serverfault.com/questions/976792/how-to-fix-partition-table-after-virt-resize-rearranges-it-kvm)

```bash
virt-rescue cloud.img
```

```bash
mkdir /mnt
mount /dev/sda3 /mnt
mount --bind /dev /mnt/dev
mount --bind /proc /mnt/proc
mount --bind /sys /mnt/sys
chroot /mnt
grub-install /dev/sda
exit
```