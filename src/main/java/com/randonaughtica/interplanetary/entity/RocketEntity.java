package com.randonaughtica.interplanetary.entity;

import com.randonaughtica.interplanetary.body.CelestialBodies;
import com.randonaughtica.interplanetary.body.CelestialBody;
import com.randonaughtica.interplanetary.registry.ModItems;
import com.randonaughtica.interplanetary.world.GravityHandler;
import com.randonaughtica.interplanetary.world.SpaceTravel;
import net.minecraft.entity.Dismounting;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityPose;
import net.minecraft.entity.EntityType;
import net.minecraft.entity.LivingEntity;
import net.minecraft.entity.MovementType;
import net.minecraft.entity.damage.DamageSource;
import net.minecraft.entity.data.DataTracker;
import net.minecraft.entity.data.TrackedData;
import net.minecraft.entity.data.TrackedDataHandlerRegistry;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NbtCompound;
import net.minecraft.network.packet.s2c.play.SubtitleS2CPacket;
import net.minecraft.network.packet.s2c.play.TitleS2CPacket;
import net.minecraft.particle.ParticleTypes;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.sound.SoundCategory;
import net.minecraft.sound.SoundEvents;
import net.minecraft.text.Text;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Formatting;
import net.minecraft.util.Hand;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Direction;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.World;
import org.jetbrains.annotations.Nullable;

/**
 * A rideable rocket. Board it, fuel it, open the flight computer (star map) and pick a destination:
 * the rocket counts down, blasts off, and lands on the chosen world with you inside.
 */
public class RocketEntity extends Entity {
    public static final int MAX_FUEL = 100;
    public static final int FUEL_PER_CANISTER = 25;
    public static final int COUNTDOWN_TICKS = 60;
    public static final int ASCENT_TICKS = 110;

    public enum State {
        IDLE, COUNTDOWN, LAUNCHING, LANDING;

        static State byId(int id) {
            State[] values = values();
            return id >= 0 && id < values.length ? values[id] : IDLE;
        }
    }

    private static final TrackedData<Integer> TIER = DataTracker.registerData(RocketEntity.class,
            TrackedDataHandlerRegistry.INTEGER);
    private static final TrackedData<Integer> FUEL = DataTracker.registerData(RocketEntity.class,
            TrackedDataHandlerRegistry.INTEGER);
    private static final TrackedData<Integer> STATE = DataTracker.registerData(RocketEntity.class,
            TrackedDataHandlerRegistry.INTEGER);

    @Nullable
    private String destination;
    private int stateTicks;
    private long lastHitTime;

    public RocketEntity(EntityType<? extends RocketEntity> type, World world) {
        super(type, world);
    }

    // ------------------------------------------------------------------ data

    @Override
    protected void initDataTracker(DataTracker.Builder builder) {
        builder.add(TIER, 1);
        builder.add(FUEL, 0);
        builder.add(STATE, State.IDLE.ordinal());
    }

    @Override
    public void onTrackedDataSet(TrackedData<?> data) {
        super.onTrackedDataSet(data);
        if (STATE.equals(data)) {
            stateTicks = 0;
        }
    }

    public int getTier() {
        return dataTracker.get(TIER);
    }

    public void setTier(int tier) {
        dataTracker.set(TIER, Math.max(1, Math.min(3, tier)));
    }

    public int getFuel() {
        return dataTracker.get(FUEL);
    }

    public void setFuel(int fuel) {
        dataTracker.set(FUEL, Math.max(0, Math.min(MAX_FUEL, fuel)));
    }

    public State getState() {
        return State.byId(dataTracker.get(STATE));
    }

    private void setState(State state) {
        dataTracker.set(STATE, state.ordinal());
        stateTicks = 0;
    }

    /** Ticks spent in the current state (also tracked on the client, for animations). */
    public int getStateTicks() {
        return stateTicks;
    }

    @Override
    protected void readCustomDataFromNbt(NbtCompound nbt) {
        setTier(nbt.getInt("Tier"));
        setFuel(nbt.getInt("Fuel"));
        // A rocket saved mid-flight finishes by landing where it is.
        if (nbt.getBoolean("Landing")) {
            setState(State.LANDING);
        }
    }

    @Override
    protected void writeCustomDataToNbt(NbtCompound nbt) {
        nbt.putInt("Tier", getTier());
        nbt.putInt("Fuel", getFuel());
        State state = getState();
        nbt.putBoolean("Landing", state == State.LANDING || state == State.LAUNCHING);
    }

    // ------------------------------------------------------------------ flight control

    /** Starts the launch countdown towards the given destination. Fuel must already be paid. */
    public void startCountdown(String destinationId) {
        this.destination = destinationId;
        setState(State.COUNTDOWN);
        getWorld().playSound(null, getX(), getY(), getZ(), SoundEvents.BLOCK_BEACON_ACTIVATE,
                SoundCategory.NEUTRAL, 1.5F, 0.8F);
    }

    /** Puts a freshly arrived rocket into its descent. */
    public void beginLanding() {
        setState(State.LANDING);
        setVelocity(0, -1.0, 0);
    }

    public void copyRocketDataFrom(RocketEntity other) {
        setTier(other.getTier());
        setFuel(other.getFuel());
    }

    @Override
    public void tick() {
        super.tick();
        stateTicks++;
        if (getWorld().isClient) {
            spawnEngineParticles();
        } else {
            serverTick();
        }
    }

    private void serverTick() {
        Entity passenger = getFirstPassenger();
        switch (getState()) {
            case IDLE -> {
                noClip = false;
                fallAndMove();
            }
            case COUNTDOWN -> {
                if (!(passenger instanceof ServerPlayerEntity player)) {
                    abortLaunch();
                    return;
                }
                if (stateTicks % 20 == 1) {
                    int secondsLeft = 3 - stateTicks / 20;
                    if (secondsLeft > 0) {
                        player.networkHandler.sendPacket(new TitleS2CPacket(
                                Text.literal(String.valueOf(secondsLeft)).formatted(Formatting.GOLD, Formatting.BOLD)));
                        getWorld().playSound(null, getX(), getY(), getZ(), SoundEvents.BLOCK_LEVER_CLICK,
                                SoundCategory.NEUTRAL, 1.0F, 1.6F);
                    }
                }
                fallAndMove();
                if (stateTicks >= COUNTDOWN_TICKS) {
                    setState(State.LAUNCHING);
                    setVelocity(0, 0.05, 0);
                    player.networkHandler.sendPacket(new TitleS2CPacket(
                            Text.translatable("message.interplanetary.rocket.liftoff").formatted(Formatting.RED, Formatting.BOLD)));
                    CelestialBody target = destination == null ? null : CelestialBodies.get(destination);
                    if (target != null) {
                        player.networkHandler.sendPacket(new SubtitleS2CPacket(
                                Text.translatable("message.interplanetary.rocket.bound_for", target.displayName())));
                    }
                    getWorld().playSound(null, getX(), getY(), getZ(), SoundEvents.ENTITY_FIREWORK_ROCKET_LAUNCH,
                            SoundCategory.NEUTRAL, 4.0F, 0.5F);
                    getWorld().playSound(null, getX(), getY(), getZ(), SoundEvents.ENTITY_LIGHTNING_BOLT_THUNDER,
                            SoundCategory.NEUTRAL, 2.0F, 0.6F);
                }
            }
            case LAUNCHING -> {
                if (!(passenger instanceof ServerPlayerEntity player)) {
                    // The pilot bailed out: the rocket falls back down.
                    noClip = false;
                    setState(State.IDLE);
                    return;
                }
                noClip = true;
                double vy = Math.min(getVelocity().y + 0.045, 2.5);
                setVelocity(0, vy, 0);
                move(MovementType.SELF, getVelocity());
                if (stateTicks % 8 == 0) {
                    getWorld().playSound(null, getX(), getY(), getZ(), SoundEvents.ENTITY_BLAZE_SHOOT,
                            SoundCategory.NEUTRAL, 2.0F, 0.5F);
                }
                if (stateTicks >= ASCENT_TICKS || getY() > getWorld().getTopY() + 120) {
                    arrive(player);
                }
            }
            case LANDING -> {
                noClip = false;
                int ground = distanceToGround(32);
                double target = ground < 0 ? -1.0 : (ground > 16 ? -0.7 : -0.12 - ground * 0.035);
                double vy = getVelocity().y;
                vy += (target - vy) * 0.25;
                setVelocity(0, vy, 0);
                move(MovementType.SELF, getVelocity());
                if (passenger != null) {
                    passenger.fallDistance = 0;
                }
                if (isOnGround() || stateTicks > 1200) {
                    setState(State.IDLE);
                    setVelocity(Vec3d.ZERO);
                    getWorld().playSound(null, getX(), getY(), getZ(), SoundEvents.BLOCK_ANVIL_LAND,
                            SoundCategory.NEUTRAL, 0.8F, 0.6F);
                    if (passenger instanceof ServerPlayerEntity player) {
                        CelestialBody here = CelestialBodies.byWorld(getWorld());
                        player.sendMessage(here != null
                                ? Text.translatable("message.interplanetary.rocket.touchdown", here.displayName()).formatted(Formatting.GREEN)
                                : Text.translatable("message.interplanetary.rocket.touchdown_unknown").formatted(Formatting.GREEN), true);
                    }
                }
            }
        }
    }

    private void arrive(ServerPlayerEntity player) {
        CelestialBody body = destination == null ? null : CelestialBodies.get(destination);
        if (body == null || player.getServer() == null || player.getServer().getWorld(body.worldKey()) == null) {
            player.sendMessage(Text.translatable("message.interplanetary.rocket.navigation_error").formatted(Formatting.RED), true);
            beginLanding();
            return;
        }
        SpaceTravel.completeFlight(this, player, body);
    }

    private void abortLaunch() {
        setState(State.IDLE);
        destination = null;
    }

    private void fallAndMove() {
        Vec3d velocity = getVelocity();
        double gravity = 0.04 * GravityHandler.gravityFactor(getWorld());
        double vy = isOnGround() && velocity.y <= 0 ? 0 : (velocity.y - gravity) * 0.98;
        setVelocity(velocity.x * 0.5, vy, velocity.z * 0.5);
        move(MovementType.SELF, getVelocity());
    }

    /** Blocks between the rocket and the ground below, or -1 if there is no ground within {@code max} blocks. */
    private int distanceToGround(int max) {
        BlockPos.Mutable pos = getBlockPos().mutableCopy();
        for (int i = 0; i < max; i++) {
            pos.move(Direction.DOWN);
            if (pos.getY() < getWorld().getBottomY()) {
                return -1;
            }
            if (!getWorld().getBlockState(pos).getCollisionShape(getWorld(), pos).isEmpty()
                    || !getWorld().getFluidState(pos).isEmpty()) {
                return i;
            }
        }
        return -1;
    }

    private void spawnEngineParticles() {
        World world = getWorld();
        State state = getState();
        if (state == State.COUNTDOWN) {
            for (int i = 0; i < 3; i++) {
                world.addParticle(ParticleTypes.LARGE_SMOKE,
                        getX() + (random.nextDouble() - 0.5) * 1.6, getY() + 0.1, getZ() + (random.nextDouble() - 0.5) * 1.6,
                        (random.nextDouble() - 0.5) * 0.25, 0.02, (random.nextDouble() - 0.5) * 0.25);
            }
            if (stateTicks > COUNTDOWN_TICKS - 25) {
                world.addParticle(ParticleTypes.FLAME, getX(), getY() + 0.1, getZ(),
                        (random.nextDouble() - 0.5) * 0.2, -0.05, (random.nextDouble() - 0.5) * 0.2);
            }
        } else if (state == State.LAUNCHING || state == State.LANDING) {
            int count = state == State.LAUNCHING ? 8 : 4;
            for (int i = 0; i < count; i++) {
                double ox = (random.nextDouble() - 0.5) * 0.4;
                double oz = (random.nextDouble() - 0.5) * 0.4;
                world.addParticle(ParticleTypes.FLAME, getX() + ox, getY() - 0.1, getZ() + oz,
                        ox * 0.3, -0.5 - random.nextDouble() * 0.5, oz * 0.3);
                world.addParticle(random.nextBoolean() ? ParticleTypes.LARGE_SMOKE : ParticleTypes.CLOUD,
                        getX() + ox * 2, getY() - 0.6, getZ() + oz * 2,
                        ox * 0.5, -0.2 - random.nextDouble() * 0.3, oz * 0.5);
            }
        }
    }

    // ------------------------------------------------------------------ interaction

    @Override
    public ActionResult interact(PlayerEntity player, Hand hand) {
        ItemStack stack = player.getStackInHand(hand);
        World world = getWorld();
        if (stack.isOf(ModItems.ROCKET_FUEL)) {
            if (!world.isClient) {
                if (getFuel() >= MAX_FUEL) {
                    player.sendMessage(Text.translatable("message.interplanetary.rocket.tank_full")
                            .formatted(Formatting.YELLOW), true);
                } else {
                    setFuel(getFuel() + FUEL_PER_CANISTER);
                    stack.decrementUnlessCreative(1, player);
                    world.playSound(null, getX(), getY(), getZ(), SoundEvents.ITEM_BUCKET_EMPTY_LAVA,
                            SoundCategory.NEUTRAL, 1.0F, 1.3F);
                    player.sendMessage(Text.translatable("message.interplanetary.rocket.fuel", getFuel(), MAX_FUEL)
                            .formatted(Formatting.AQUA), true);
                }
            }
            return ActionResult.success(world.isClient);
        }
        if (player.shouldCancelInteraction() || hasPassengers() || getState() != State.IDLE) {
            return ActionResult.PASS;
        }
        if (!world.isClient) {
            if (player.startRiding(this)) {
                player.sendMessage(Text.translatable("message.interplanetary.rocket.boarded",
                        Text.keybind("key.interplanetary.flight_computer")).formatted(Formatting.AQUA), true);
            }
        }
        return ActionResult.success(world.isClient);
    }

    @Override
    public boolean damage(DamageSource source, float amount) {
        if (isInvulnerableTo(source)) {
            return false;
        }
        if (getWorld().isClient || isRemoved()) {
            return true;
        }
        if (getState() != State.IDLE || hasPassengers()
                || !(source.getAttacker() instanceof PlayerEntity player)) {
            return false;
        }
        // Two quick hits pick the rocket back up, so it is not broken by accident.
        long now = getWorld().getTime();
        if (!player.getAbilities().creativeMode && now - lastHitTime > 10) {
            lastHitTime = now;
            getWorld().playSound(null, getX(), getY(), getZ(), SoundEvents.ENTITY_ARMOR_STAND_HIT,
                    SoundCategory.NEUTRAL, 1.0F, 0.6F);
            return true;
        }
        if (!player.getAbilities().creativeMode) {
            dropStack(new ItemStack(ModItems.rocketForTier(getTier())));
            int canisters = getFuel() / FUEL_PER_CANISTER;
            if (canisters > 0) {
                dropStack(new ItemStack(ModItems.ROCKET_FUEL, canisters));
            }
        }
        getWorld().playSound(null, getX(), getY(), getZ(), SoundEvents.ENTITY_ARMOR_STAND_BREAK,
                SoundCategory.NEUTRAL, 1.0F, 0.6F);
        discard();
        return true;
    }

    @Override
    public ItemStack getPickBlockStack() {
        return new ItemStack(ModItems.rocketForTier(getTier()));
    }

    @Override
    public boolean canHit() {
        return !isRemoved();
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    public boolean canUsePortals(boolean allowVehicles) {
        return false;
    }

    @Override
    public Vec3d updatePassengerForDismount(LivingEntity passenger) {
        Direction facing = getHorizontalFacing();
        Direction[] order = {facing, facing.rotateYClockwise(), facing.rotateYCounterclockwise(), facing.getOpposite()};
        for (Direction dir : order) {
            double x = getX() + dir.getOffsetX() * 1.4;
            double z = getZ() + dir.getOffsetZ() * 1.4;
            BlockPos base = BlockPos.ofFloored(x, getY(), z);
            for (int dy : new int[]{0, 1, -1, 2}) {
                BlockPos pos = base.up(dy);
                double floor = getWorld().getDismountHeight(pos);
                if (Dismounting.canDismountInBlock(floor)) {
                    Vec3d target = new Vec3d(x, pos.getY() + floor, z);
                    if (Dismounting.canPlaceEntityAt(getWorld(), passenger,
                            passenger.getBoundingBox(EntityPose.STANDING).offset(target))) {
                        return target;
                    }
                }
            }
        }
        return super.updatePassengerForDismount(passenger);
    }
}
