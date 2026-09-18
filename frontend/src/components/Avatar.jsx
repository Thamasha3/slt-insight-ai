import { avatarSrc, userInitials } from "../utils/avatar.js";

export default function Avatar({ name, src, size = "md", className = "" }) {
  const pixels = size === "lg" ? "h-24 w-24 text-2xl" : size === "sm" ? "h-10 w-10 text-xs" : "h-12 w-12 text-sm";
  const resolved = avatarSrc(src);

  if (resolved) {
    return (
      <img
        src={resolved}
        alt={name ? `${name} profile picture` : "Profile picture"}
        className={`${pixels} shrink-0 rounded-full object-cover ring-2 ring-white ${className}`}
      />
    );
  }

  return (
    <div
      className={`flex ${pixels} shrink-0 items-center justify-center rounded-full bg-slt-blue/10 font-semibold text-slt-blue ${className}`}
      aria-hidden={!name}
    >
      {userInitials(name)}
    </div>
  );
}
